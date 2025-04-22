# workflow.py
import os
import json
import logging
import autogen
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-3.5-turbo"  # Or "gpt-3.5-turbo" for lower cost, gpt-4-turbo

def load_knowledge_base():
    """Load the investment knowledge base."""
    knowledge_path = "data/investment_knowledge.txt"
    
    if os.path.exists(knowledge_path):
        with open(knowledge_path, "r") as f:
            return f.read()
    else:
        # Create a basic knowledge base if the file doesn't exist
        os.makedirs(os.path.dirname(knowledge_path), exist_ok=True)
        
        knowledge_base = """
        # Basic Investment Knowledge
        
        ## ETFs
        - VTI (Vanguard Total Stock Market): Broad US stock market exposure, medium risk
        - BND (Vanguard Total Bond): US bond market exposure, low risk
        - VXUS (Vanguard Total International Stock): International stock exposure, medium-high risk
        
        ## Robo-Advisors
        - Betterment: Automated investing with tax optimization, adjustable risk
        - Wealthfront: Automated investing with financial planning tools, adjustable risk
        """
        
        with open(knowledge_path, "w") as f:
            f.write(knowledge_base)
        
        return knowledge_base

def process_investment_request(user_input):
    """Process an investment request using the autogen agents."""
    # Configure autogen
    config_list = [
        {
            "model": OPENAI_MODEL,
            "api_key": OPENAI_API_KEY,
        }
    ]
    
    # Load the knowledge base
    knowledge_base = load_knowledge_base()
    
    print("\n[Step 1] Extracting investment goals...")
    
    # Step 1: Extract structured goal - Passive Goal Creator pattern
    goal_creator = autogen.AssistantAgent(
        name="GoalCreator",
        llm_config={
            "config_list": config_list,
            "temperature": 0.1
        },
        system_message="""You are a financial goal extraction specialist implementing the Passive Goal Creator pattern.
        Your task is to analyze the user's investment request and extract structured information about their investment goals.
        
        Extract the following information:
        - goal_type: What are they investing for? (retirement, education, house, general wealth, etc.)
        - investment_horizon: The time frame (short-term, medium-term, long-term)
        - risk_tolerance: Their risk appetite (low, medium, high)
        - investment_preferences: Any specific preferences mentioned (e.g., ETF, stocks, bonds, real estate, robo-advisor)
        
        Respond with a valid JSON object only, following this structure:
        {"goal_type": "...", "investment_horizon": "...", "risk_tolerance": "...", "investment_preferences": [...]}
        
        If certain information is not explicitly provided, use reasonable defaults based on their other stated preferences.
        """
    )
    
    user_proxy = autogen.UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0
    )
    
    # Extract structured goal
    user_proxy.initiate_chat(
        goal_creator, 
        message=f"I need investment advice: {user_input}"
    )
    
    goal_creator_response = goal_creator.last_message()["content"]
    
    # Extract the JSON object from the response
    try:
        json_start = goal_creator_response.find('{')
        json_end = goal_creator_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            structured_goal = json.loads(goal_creator_response[json_start:json_end])
            print(f"Structured goal: {json.dumps(structured_goal, indent=2)}")
        else:
            raise ValueError("Failed to extract JSON from response")
    except Exception as e:
        print(f"Error extracting structured goal: {e}")
        return None
    
    print("\n[Step 2] Retrieving investment options...")
    
    # Step 2: Retrieve investment options - RAG pattern
    rag_agent = autogen.AssistantAgent(
        name="RAGAgent",
        llm_config={
            "config_list": config_list,
            "temperature": 0.1
        },
        system_message=f"""You are a financial investment advisor implementing the Retrieval Augmented Generation pattern.
        
        Given a structured goal JSON, use the investment knowledge base to identify suitable investment options.
        The knowledge base contains information about various ETFs, robo-advisors, and investment strategies.
        
        INVESTMENT KNOWLEDGE BASE:
        {knowledge_base}
        
        Based on the user's goals, provide:
        1. A list of suitable investment products (ETFs or robo-advisors)
        2. Current market insights relevant to the user's goals
        3. A summary of the key considerations
        
        Format your response as a JSON object with the following structure:
        {{
            "products": [
                {{"name": "...", "type": "...", "risk_level": "...", "description": "..."}}
            ],
            "market_insights": "...",
            "key_considerations": "..."
        }}
        """
    )
    
    # Get investment options
    user_proxy.initiate_chat(
        rag_agent, 
        message=f"Based on this structured goal, what investment options would you recommend? {json.dumps(structured_goal)}"
    )
    
    rag_response = rag_agent.last_message()["content"]
    
    # Extract the JSON object from the response
    try:
        json_start = rag_response.find('{')
        json_end = rag_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            investment_options = json.loads(rag_response[json_start:json_end])
            print(f"Found {len(investment_options.get('products', []))} investment options")
        else:
            raise ValueError("Failed to extract JSON from response")
    except Exception as e:
        print(f"Error extracting investment options: {e}")
        return None
    
    print("\n[Step 3] Running voting-based cooperation process...")
    
    # Step 3: Voting-Based Cooperation pattern
    # Create specialist agents for voting
    investment_specialist = autogen.AssistantAgent(
        name="InvestmentSpecialist",
        llm_config={
            "config_list": config_list,
            "temperature": 0.2
        },
        system_message="""You are an investment specialist focusing on expected returns and portfolio diversification.
        
        Evaluate investment options based solely on their potential for returns and diversification.
        Do not consider risk tolerance (another agent will do that).
        
        Your evaluation should result in a vote on each product with a score from 1-10 
        (10 being highest expected returns and best diversification).
        
        Also provide a brief rationale for your votes.
        
        Format your response as a JSON object with the following structure:
        {
            "product_votes": [
                {"product_name": "...", "score": X, "rationale": "..."}
            ],
            "overall_assessment": "..."
        }
        """
    )
    
    # Get votes from Investment Specialist
    user_proxy.initiate_chat(
        investment_specialist, 
        message=f"Please evaluate these investment options based on returns and diversification: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}"
    )
    
    investment_response = investment_specialist.last_message()["content"]
    
    # Extract the JSON object from the response
    try:
        json_start = investment_response.find('{')
        json_end = investment_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            investment_votes = json.loads(investment_response[json_start:json_end])
            print(f"Received votes from Investment Specialist")
        else:
            raise ValueError("Failed to extract JSON from response")
    except Exception as e:
        print(f"Error extracting investment votes: {e}")
        return None
    
    # Risk Specialist
    risk_specialist = autogen.AssistantAgent(
        name="RiskSpecialist",
        llm_config={
            "config_list": config_list,
            "temperature": 0.2
        },
        system_message="""You are a risk assessment specialist focusing on investment volatility and risk profiles.
        
        Evaluate investment options based solely on their risk profiles and how well they align with the 
        user's stated risk tolerance. Focus especially on potential downside risks.
        
        Your evaluation should result in a vote on each product with a score from 1-10 
        (10 being perfect alignment with the user's risk tolerance).
        
        Also provide a brief rationale for your votes.
        
        Format your response as a JSON object with the following structure:
        {
            "product_votes": [
                {"product_name": "...", "score": X, "rationale": "..."}
            ],
            "overall_assessment": "..."
        }
        """
    )
    
    # Get votes from Risk Specialist
    user_proxy.initiate_chat(
        risk_specialist, 
        message=f"Please evaluate these investment options based on risk alignment: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}"
    )
    
    risk_response = risk_specialist.last_message()["content"]
    
    # Extract the JSON object from the response
    try:
        json_start = risk_response.find('{')
        json_end = risk_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            risk_votes = json.loads(risk_response[json_start:json_end])
            print(f"Received votes from Risk Specialist")
        else:
            raise ValueError("Failed to extract JSON from response")
    except Exception as e:
        print(f"Error extracting risk votes: {e}")
        return None
    
    # Goal Specialist
    goal_specialist = autogen.AssistantAgent(
        name="GoalSpecialist",
        llm_config={
            "config_list": config_list,
            "temperature": 0.2
        },
        system_message="""You are a financial planner specializing in matching investment strategies to specific goals.
        
        Evaluate investment options based solely on how well they align with the user's specific goal 
        (e.g., retirement, education, house purchase) and investment horizon.
        
        Your evaluation should result in a vote on each product with a score from 1-10 
        (10 being perfect alignment with the user's goal and horizon).
        
        Also provide a brief rationale for your votes.
        
        Format your response as a JSON object with the following structure:
        {
            "product_votes": [
                {"product_name": "...", "score": X, "rationale": "..."}
            ],
            "overall_assessment": "..."
        }
        """
    )
    
    # Get votes from Goal Specialist
    user_proxy.initiate_chat(
        goal_specialist, 
        message=f"Please evaluate these investment options based on goal alignment: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}"
    )
    
    goal_response = goal_specialist.last_message()["content"]
    
    # Extract the JSON object from the response
    try:
        json_start = goal_response.find('{')
        json_end = goal_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            goal_votes = json.loads(goal_response[json_start:json_end])
            print(f"Received votes from Goal Specialist")
        else:
            raise ValueError("Failed to extract JSON from response")
    except Exception as e:
        print(f"Error extracting goal votes: {e}")
        return None
    
    print("\n[Step 4] Coordinating votes and generating final strategy...")
    
    # Record all votes with agent identities for accountability
    voting_record = {
        "votes": [
            {"agent": "InvestmentSpecialist", "votes": investment_votes},
            {"agent": "RiskSpecialist", "votes": risk_votes},
            {"agent": "GoalSpecialist", "votes": goal_votes}
        ],
        "timestamp": str(import_datetime().now())
    }
    
    # Step 4: Coordinate voting - Finalize strategy
    voting_coordinator = autogen.AssistantAgent(
        name="VotingCoordinator",
        llm_config={
            "config_list": config_list,
            "temperature": 0.1
        },
        system_message="""You are a financial advisor implementing the Voting-Based Cooperation pattern.
        
        Based on the votes and assessments from the Investment, Risk, and Goal specialists, create a final 
        investment strategy recommendation.
        
        Include:
        1. A descriptive summary of the recommendation
        2. Asset allocation percentages
        3. Specific recommended products
        4. Clear rationale for the recommendation
        5. The voting record showing how each specialist voted
        
        Format your response as a JSON object with the following structure:
        {
            "description": "...",
            "allocation": {
                "asset_class1": percentage,
                "asset_class2": percentage,
                ...
            },
            "products": [
                {"name": "...", "description": "...", "percentage": ...}
            ],
            "rationale": "...",
            "voting_record": {...}
        }
        """
    )
    
    # Get final strategy
    user_proxy.initiate_chat(
        voting_coordinator, 
        message=f"""
        Please create a final investment strategy based on the following votes:
        
        Goal: {json.dumps(structured_goal)}
        Options: {json.dumps(investment_options)}
        
        Voting Record: {json.dumps(voting_record)}
        """
    )
    
    coordinator_response = voting_coordinator.last_message()["content"]
    
    # Extract the JSON object from the response
    try:
        json_start = coordinator_response.find('{')
        json_end = coordinator_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            strategy = json.loads(coordinator_response[json_start:json_end])
            print(f"Final strategy generated")
        else:
            raise ValueError("Failed to extract JSON from response")
    except Exception as e:
        print(f"Error extracting strategy: {e}")
        return None
    
    # Step 5: Format the presentation
    print("\n[Step 5] Formatting presentation...")
    
    presentation_agent = autogen.AssistantAgent(
        name="PresentationAgent",
        llm_config={
            "config_list": config_list,
            "temperature": 0.3
        },
        system_message="""You are responsible for formatting the investment strategy recommendation in a clear,
        professional, and user-friendly manner. 
        
        Take the technical strategy JSON and convert it into a well-structured, easy-to-understand presentation
        with appropriate sections and formatting.
        """
    )
    
    # Get formatted presentation
    user_proxy.initiate_chat(
        presentation_agent, 
        message=f"Please format this investment strategy for presentation to the user: {json.dumps(strategy)}"
    )
    
    presentation = presentation_agent.last_message()["content"]
    
    return {
        "structured_goal": structured_goal,
        "investment_options": investment_options,
        "strategy": strategy,
        "presentation": presentation
    }

def process_feedback(user_feedback, structured_goal, strategy):
    """Process user feedback on the investment strategy."""
    # Configure autogen
    config_list = [
        {
            "model": OPENAI_MODEL,
            "api_key": OPENAI_API_KEY,
        }
    ]
    
    print("\n[Feedback] Processing your feedback...")
    
    # Create the feedback agent - Human Reflection pattern
    feedback_agent = autogen.AssistantAgent(
        name="FeedbackAgent",
        llm_config={
            "config_list": config_list,
            "temperature": 0.1
        },
        system_message="""You are a financial advisor implementing the Human Reflection pattern.
        
        Analyze user feedback on investment recommendations and determine:
        1. What aspects of the recommendation the user liked or disliked
        2. Any adjustments needed to the user's risk profile
        3. Any changes in investment preferences that should be noted
        4. Specific changes to make to future recommendations
        
        Format your response as a JSON object with the following structure:
        {
            "feedback_analysis": "...",
            "risk_adjustment": "higher"/"lower"/"no change",
            "preference_changes": ["...", "..."],
            "strategy_adjustments": ["...", "..."]
        }
        """
    )
    
    user_proxy = autogen.UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0
    )
    
    # Process the feedback
    user_proxy.initiate_chat(
        feedback_agent, 
        message=f"""
        Process this feedback on an investment recommendation:
        
        Original Goal: {json.dumps(structured_goal)}
        Recommended Strategy: {json.dumps(strategy)}
        User Feedback: {user_feedback}
        """
    )
    
    feedback_response = feedback_agent.last_message()["content"]
    
    # Extract the JSON object from the response
    try:
        json_start = feedback_response.find('{')
        json_end = feedback_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            analysis = json.loads(feedback_response[json_start:json_end])
            return analysis
        else:
            raise ValueError("Failed to extract JSON from response")
    except Exception as e:
        print(f"Error extracting feedback analysis: {e}")
        return {
            "feedback_analysis": "Unable to analyze feedback properly.",
            "risk_adjustment": "no change",
            "preference_changes": [],
            "strategy_adjustments": []
        }

def import_datetime():
    import datetime
    return datetime.datetime

def main():
    print("Welcome to the Investment Strategy Advisor!")
    print("Please describe your investment goals (e.g., 'I want to invest for retirement with low risk').")
    print("Type 'quit' to exit.")
    
    while True:
        user_input = input("\nYour investment goal: ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Thank you for using the Investment Strategy Advisor!")
            break
        
        if user_input.strip():
            try:
                print("\nProcessing your request...")
                result = process_investment_request(user_input)
                
                if result:
                    # Present the results
                    print("\n" + "=" * 80)
                    print(result["presentation"])
                    print("=" * 80)
                    
                    # Ask for feedback
                    feedback = input("\nWhat do you think of this recommendation? ")
                    
                    if feedback.strip():
                        # Process the feedback
                        analysis = process_feedback(
                            feedback,
                            result["structured_goal"],
                            result["strategy"]
                        )
                        
                        print("\nThank you for your feedback! Your preferences have been updated.")
                        print(f"\nFeedback analysis: {analysis['feedback_analysis']}")
                        
                        if analysis.get("risk_adjustment") != "no change":
                            print(f"Risk adjustment: {analysis['risk_adjustment']}")
                        
                        if analysis.get("preference_changes"):
                            print(f"Preference changes: {', '.join(analysis['preference_changes'])}")
                        
                        if analysis.get("strategy_adjustments"):
                            print(f"Strategy adjustments for next time: {', '.join(analysis['strategy_adjustments'])}")
                        
                        print("\nWould you like to see another investment strategy? Please provide a new goal.")
            except Exception as e:
                print(f"Error processing your request: {e}")
                print("Please try again with a clearer investment goal.")

if __name__ == "__main__":
    main()