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
OPENAI_MODEL = "gpt-3.5-turbo" # Or "gpt-3.5-turbo" for lower cost, "gpt-4-turbo"

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

def setup_agents():
    """Set up the autogen agents for the investment strategy advisor."""
    # Configure autogen
    config_list = [
        {
            "model": OPENAI_MODEL,
            "api_key": OPENAI_API_KEY,
        }
    ]
    
    # Load the knowledge base
    knowledge_base = load_knowledge_base()
    
    # Create the user proxy agent
    user_proxy = autogen.UserProxyAgent(
        name="User",
        human_input_mode="TERMINATE",
        system_message="I am a user seeking investment advice.",
        code_execution_config=False,
    )
    
    # Create the goal creator agent - Passive Goal Creator pattern
    goal_creator = autogen.AssistantAgent(
        name="GoalCreator",
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
        """,
        llm_config={"config_list": config_list},
    )
    
    # Create the RAG agent - Retrieval Augmented Generation pattern
    rag_agent = autogen.AssistantAgent(
        name="RAGAgent",
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
        """,
        llm_config={"config_list": config_list},
    )
    
    # Create specialist agents for voting
    investment_specialist = autogen.AssistantAgent(
        name="InvestmentSpecialist",
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
        """,
        llm_config={"config_list": config_list},
    )
    
    risk_specialist = autogen.AssistantAgent(
        name="RiskSpecialist",
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
        """,
        llm_config={"config_list": config_list},
    )
    
    goal_specialist = autogen.AssistantAgent(
        name="GoalSpecialist",
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
        """,
        llm_config={"config_list": config_list},
    )
    
    # Create the voting coordinator - Voting-Based Cooperation pattern
    voting_coordinator = autogen.AssistantAgent(
        name="VotingCoordinator",
        system_message="""You are a financial advisor implementing the Voting-Based Cooperation pattern.
        
        Based on the votes and assessments from the Investment, Risk, and Goal specialists, create a final 
        investment strategy recommendation.
        
        Include:
        1. A descriptive summary of the recommendation
        2. Asset allocation percentages
        3. Specific recommended products
        4. Clear rationale for the recommendation
        
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
            "rationale": "..."
        }
        """,
        llm_config={"config_list": config_list},
    )
    
    # Create the feedback agent - Human Reflection pattern
    feedback_agent = autogen.AssistantAgent(
        name="FeedbackAgent",
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
        """,
        llm_config={"config_list": config_list},
    )
    
    # Create the presentation agent for formatting results
    presentation_agent = autogen.AssistantAgent(
        name="PresentationAgent",
        system_message="""You are responsible for formatting the investment strategy recommendation in a clear,
        professional, and user-friendly manner. 
        
        Take the technical strategy JSON and convert it into a well-structured, easy-to-understand presentation
        with appropriate sections and formatting.
        """,
        llm_config={"config_list": config_list},
    )
    
    return {
        "user_proxy": user_proxy,
        "goal_creator": goal_creator,
        "rag_agent": rag_agent,
        "investment_specialist": investment_specialist,
        "risk_specialist": risk_specialist,
        "goal_specialist": goal_specialist,
        "voting_coordinator": voting_coordinator,
        "feedback_agent": feedback_agent,
        "presentation_agent": presentation_agent,
    }

def process_investment_request(user_input):
    """Process an investment request using the autogen agents."""
    # Set up the agents
    agents = setup_agents()
    
    # Extract the structured goal - Passive Goal Creator pattern
    agents["user_proxy"].initiate_chat(
        agents["goal_creator"],
        message=f"I need investment advice: {user_input}"
    )
    
    # Extract the JSON object from the response
    goal_creator_response = agents["goal_creator"].last_message()["content"]
    json_start = goal_creator_response.find('{')
    json_end = goal_creator_response.rfind('}') + 1
    structured_goal = json.loads(goal_creator_response[json_start:json_end])
    
    # Retrieve investment options - RAG pattern
    agents["user_proxy"].initiate_chat(
        agents["rag_agent"],
        message=f"Based on this structured goal, what investment options would you recommend? {json.dumps(structured_goal)}"
    )
    
    # Extract the JSON object from the response
    rag_response = agents["rag_agent"].last_message()["content"]
    json_start = rag_response.find('{')
    json_end = rag_response.rfind('}') + 1
    investment_options = json.loads(rag_response[json_start:json_end])
    
    # Get votes from specialists
    # Investment Specialist
    agents["user_proxy"].initiate_chat(
        agents["investment_specialist"],
        message=f"Please evaluate these investment options based on returns and diversification: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}"
    )
    
    investment_specialist_response = agents["investment_specialist"].last_message()["content"]
    json_start = investment_specialist_response.find('{')
    json_end = investment_specialist_response.rfind('}') + 1
    investment_votes = json.loads(investment_specialist_response[json_start:json_end])
    
    # Risk Specialist
    agents["user_proxy"].initiate_chat(
        agents["risk_specialist"],
        message=f"Please evaluate these investment options based on risk alignment: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}"
    )
    
    risk_specialist_response = agents["risk_specialist"].last_message()["content"]
    json_start = risk_specialist_response.find('{')
    json_end = risk_specialist_response.rfind('}') + 1
    risk_votes = json.loads(risk_specialist_response[json_start:json_end])
    
    # Goal Specialist
    agents["user_proxy"].initiate_chat(
        agents["goal_specialist"],
        message=f"Please evaluate these investment options based on goal alignment: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}"
    )
    

    goal_specialist_response = agents["goal_specialist"].last_message()["content"]
    json_start = goal_specialist_response.find('{')
    json_end = goal_specialist_response.rfind('}') + 1
    goal_votes = json.loads(goal_specialist_response[json_start:json_end])
    
    # Coordinate voting - Voting-Based Cooperation pattern
    agents["user_proxy"].initiate_chat(
        agents["voting_coordinator"],
        message=f"""
        Please create a final investment strategy based on the following votes:
        
        Goal: {json.dumps(structured_goal)}
        Options: {json.dumps(investment_options)}
        
        Investment Specialist votes: {json.dumps(investment_votes)}
        Risk Specialist votes: {json.dumps(risk_votes)}
        Goal Specialist votes: {json.dumps(goal_votes)}
        """
    )
    
    voting_coordinator_response = agents["voting_coordinator"].last_message()["content"]
    json_start = voting_coordinator_response.find('{')
    json_end = voting_coordinator_response.rfind('}') + 1
    strategy = json.loads(voting_coordinator_response[json_start:json_end])
    
    # Format the strategy for presentation
    agents["user_proxy"].initiate_chat(
        agents["presentation_agent"],
        message=f"Please format this investment strategy for presentation to the user: {json.dumps(strategy)}"
    )
    
    presentation = agents["presentation_agent"].last_message()["content"]
    
    return {
        "structured_goal": structured_goal,
        "investment_options": investment_options,
        "strategy": strategy,
        "presentation": presentation
    }

def process_feedback(user_feedback, structured_goal, strategy):
    """Process user feedback on the investment strategy."""
    # Set up the agents
    agents = setup_agents()
    
    # Process the feedback - Human Reflection pattern
    agents["user_proxy"].initiate_chat(
        agents["feedback_agent"],
        message=f"""
        Process this feedback on an investment recommendation:
        
        Original Goal: {json.dumps(structured_goal)}
        Recommended Strategy: {json.dumps(strategy)}
        User Feedback: {user_feedback}
        """
    )
    
    feedback_agent_response = agents["feedback_agent"].last_message()["content"]
    json_start = feedback_agent_response.find('{')
    json_end = feedback_agent_response.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        analysis = json.loads(feedback_agent_response[json_start:json_end])
    else:
        analysis = {
            "feedback_analysis": "Unable to analyze feedback properly.",
            "risk_adjustment": "no change",
            "preference_changes": [],
            "strategy_adjustments": []
        }
    
    return analysis

def run_voting_process(structured_goal, investment_options):
    """
    Run a proper voting-based cooperation process as described in the research paper.
    This better implements the pattern with accountability and fairness.
    """
    # Configure autogen
    config_list = [{"model": OPENAI_MODEL, "api_key": OPENAI_API_KEY}]
    
    print("\n[Voting Process] Setting up voting for investment strategy selection...")
    
    # Create the voting coordinator
    voting_coordinator = autogen.AssistantAgent(
        name="VotingCoordinator",
        llm_config={"config_list": config_list, "temperature": 0.1},
        system_message="""You are the Voting Coordinator responsible for:
        1. Presenting investment options for agents to vote on
        2. Recording votes from each participating agent
        3. Calculating the final results based on vote counts
        4. Providing a detailed record of the voting process
        
        Create candidate investment strategies based on the investment options.
        For each investment option, create a potential strategy around it.
        Present these as clear choices for other agents to vote on.
        """
    )
    
    user_proxy = autogen.UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0
    )
    
    # Generate candidate strategies
    user_proxy.initiate_chat(
        voting_coordinator,
        message=f"""Based on this goal {json.dumps(structured_goal)} and these 
        investment options {json.dumps(investment_options)}, please create 3-5 
        distinct investment strategy candidates for agents to vote on. 
        Format each as a numbered choice with clear description."""
    )
    
    candidate_strategies = voting_coordinator.last_message()["content"]
    
    # Create voting agents
    voting_agents = []
    agent_names = [
        "InvestmentExpert", 
        "RiskAnalyst", 
        "GoalSpecialist", 
        "TaxSpecialist", 
        "MarketAnalyst"
    ]
    
    # Track votes with agent identities for accountability
    votes = {"agent_votes": []}
    
    # Create multiple agents with different perspectives
    for name in agent_names:
        voting_agent = autogen.AssistantAgent(
            name=name,
            llm_config={"config_list": config_list, "temperature": 0.2},
            system_message=f"""You are a financial specialist focusing on {name.replace("Specialist", "").replace("Expert", "").replace("Analyst", "")}.
            
            Review the candidate investment strategies and vote for the ONE you believe best meets the user's goals.
            
            Provide:
            1. Your vote (strategy number)
            2. A brief rationale for why you chose this strategy
            3. Any concerns about the strategy you've selected
            
            Your identity and vote will be recorded for accountability purposes.
            """
        )
        voting_agents.append(voting_agent)
        
        # Have each agent cast their vote
        user_proxy.initiate_chat(
            voting_agent,
            message=f"""
            User Goal: {json.dumps(structured_goal)}
            
            Candidate Strategies:
            {candidate_strategies}
            
            Please cast your vote for ONE strategy by providing its number,
            along with your rationale.
            """
        )
        
        vote_response = voting_agent.last_message()["content"]
        
        # Record the vote with agent identity
        votes["agent_votes"].append({
            "agent_name": name,
            "vote_content": vote_response,
            "timestamp": str(import_datetime().now())
        })
        
        print(f"Agent {name} has cast their vote.")
    
    # Tally votes and determine winning strategy
    user_proxy.initiate_chat(
        voting_coordinator,
        message=f"""
        The voting process is complete. Here are all votes cast by the agents:
        
        {json.dumps(votes, indent=2)}
        
        Please:
        1. Tally the votes and determine the winning strategy
        2. Create a detailed voting record showing which agent voted for what
        3. Generate the final investment strategy based on the winning candidate
        4. Include your voting record in the response for accountability
        """
    )
    
    voting_results = voting_coordinator.last_message()["content"]
    
    # Now have the coordinator formalize the winning strategy
    user_proxy.initiate_chat(
        voting_coordinator,
        message=f"""
        Based on the voting results, please formalize the winning strategy into a detailed
        investment plan. Format your response as a JSON object with:
        
        1. The voting record (which agent voted for what)
        2. The final strategy details (allocation, products, rationale)
        3. Metadata about the voting process
        
        This will serve as the official record of our voting-based cooperation process.
        """
    )
    
    final_result = voting_coordinator.last_message()["content"]
    
    # Extract the JSON object from the response
    try:
        json_start = final_result.find('{')
        json_end = final_result.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            final_strategy = json.loads(final_result[json_start:json_end])
            print(f"Voting process complete. Strategy selected by majority vote.")
            return final_strategy
        else:
            raise ValueError("Failed to extract JSON from response")
    except Exception as e:
        print(f"Error extracting voting results: {e}")
        return None

def import_datetime():
    import datetime
    return datetime

def main():
    """Main function to run the Investment Strategy Advisor."""
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
                
                print("\n" + "=" * 80)
                print(result["presentation"])
                print("=" * 80)
                
                feedback = input("\nWhat do you think of this recommendation? ")
                
                if feedback.strip():
                    print("\nProcessing your feedback...")
                    analysis = process_feedback(
                        feedback,
                        result["structured_goal"],
                        result["strategy"]
                    )
                    
                    print("\nThank you for your feedback! Your preferences have been updated.")
                    print(f"\nFeedback analysis: {analysis['feedback_analysis']}")
                    print("Would you like to see another investment strategy? Please provide a new goal.")
            except Exception as e:
                print(f"Error processing your request: {e}")
                print("Please try again with a clearer investment goal.")

if __name__ == "__main__":
    main()