import os
import json
import logging
import argparse
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import autogen
import autogen
from autogen import Agent, UserProxyAgent, AssistantAgent, GroupChat, GroupChatManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4-turbo"

class InvestmentStrategyAdvisor:
    """Main controller class for the Investment Strategy Advisor system."""
    
    def __init__(self):
        """Initialize the autogen agents and group chat."""
        # Configure autogen
        config_list = [
            {
                "model": OPENAI_MODEL,
                "api_key": OPENAI_API_KEY,
            }
        ]
        
        # Initialize the knowledge base
        self._initialize_knowledge_base()
        
        # Create agents
        self.user_proxy = UserProxyAgent(
            name="UserProxy",
            human_input_mode="NEVER",  # We'll manually handle user inputs
            is_termination_msg=lambda x: x.get("content", "") and "TASK_COMPLETE" in x.get("content", "")
        )
        
        self.passive_goal_agent = AssistantAgent(
            name="PassiveGoalAgent",
            system_message="""You are a financial goal extraction specialist. Your task is to analyze the user's 
            investment request and extract structured information about their investment goals.
            
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
        
        self.rag_agent = AssistantAgent(
            name="RAGAgent",
            system_message=f"""You are a financial investment advisor with expertise in ETFs and robo-advisors.
            
            Given a structured goal JSON, use the investment knowledge base to identify suitable investment options.
            The knowledge base contains information about various ETFs, robo-advisors, and investment strategies.
            
            INVESTMENT KNOWLEDGE BASE:
            {self.knowledge_base}
            
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
        
        self.investment_agent = AssistantAgent(
            name="InvestmentAgent",
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
        
        self.risk_agent = AssistantAgent(
            name="RiskAgent",
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
        
        self.goal_agent = AssistantAgent(
            name="GoalAgent",
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
        
        self.voting_coordinator = AssistantAgent(
            name="VotingCoordinator",
            system_message="""You are a financial advisor coordinating the recommendations from multiple specialist agents.
            
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
        
        self.feedback_agent = AssistantAgent(
            name="FeedbackAgent",
            system_message="""You are a financial advisor analyzing user feedback on investment recommendations.
            
            Analyze feedback and determine:
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
            
            End your message with TASK_COMPLETE when you have finished processing the feedback.
            """,
            llm_config={"config_list": config_list},
        )
        
        # Define the group chat
        self.agents = [
            self.user_proxy,
            self.passive_goal_agent,
            self.rag_agent,
            self.investment_agent,
            self.risk_agent,
            self.goal_agent,
            self.voting_coordinator,
            self.feedback_agent,
        ]
        
        # Create a group chat with a manager
        self.group_chat = GroupChat(
            agents=self.agents,
            messages=[],
            max_round=15
        )
        
        self.manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config={"config_list": config_list},
        )
    
    def _initialize_knowledge_base(self):
        """Load or create the investment knowledge base."""
        knowledge_path = "data/investment_knowledge.txt"
        
        if os.path.exists(knowledge_path):
            with open(knowledge_path, "r") as f:
                self.knowledge_base = f.read()
        else:
            # Create a basic knowledge base if the file doesn't exist
            os.makedirs(os.path.dirname(knowledge_path), exist_ok=True)
            
            self.knowledge_base = """
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
                f.write(self.knowledge_base)
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input through the autogen pipeline.
        
        Args:
            user_input: The user's natural language input
            
        Returns:
            A dictionary containing the final strategy
        """
        logger.info(f"Processing input: {user_input}")
        
        # Reset the chat
        self.group_chat.messages = []
        
        # Start the process with the user's input
        self.user_proxy.send(
            message=f"I need investment advice: {user_input}",
            recipient=self.passive_goal_agent
        )
        
        # Passive Goal Creator pattern
        structured_goal = self._wait_for_json_response(self.passive_goal_agent)
        logger.info(f"Structured goal: {structured_goal}")
        
        # RAG pattern
        self.user_proxy.send(
            message=f"Based on this structured goal, what investment options would you recommend? {json.dumps(structured_goal)}",
            recipient=self.rag_agent
        )
        
        investment_options = self._wait_for_json_response(self.rag_agent)
        logger.info(f"Retrieved investment options")
        
        # Voting-Based Cooperation pattern
        # 1. Get votes from Investment Agent
        self.user_proxy.send(
            message=f"Please evaluate these investment options based on returns and diversification: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}",
            recipient=self.investment_agent
        )
        investment_votes = self._wait_for_json_response(self.investment_agent)
        
        # 2. Get votes from Risk Agent
        self.user_proxy.send(
            message=f"Please evaluate these investment options based on risk alignment: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}",
            recipient=self.risk_agent
        )
        risk_votes = self._wait_for_json_response(self.risk_agent)
        
        # 3. Get votes from Goal Agent
        self.user_proxy.send(
            message=f"Please evaluate these investment options based on goal alignment: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}",
            recipient=self.goal_agent
        )
        goal_votes = self._wait_for_json_response(self.goal_agent)
        
        # 4. Coordinate voting
        self.user_proxy.send(
            message=f"""
            Please create a final investment strategy based on the following votes:
            
            Goal: {json.dumps(structured_goal)}
            Options: {json.dumps(investment_options)}
            
            Investment Specialist votes: {json.dumps(investment_votes)}
            Risk Specialist votes: {json.dumps(risk_votes)}
            Goal Specialist votes: {json.dumps(goal_votes)}
            """,
            recipient=self.voting_coordinator
        )
        
        strategy = self._wait_for_json_response(self.voting_coordinator)
        
        return {
            "structured_goal": structured_goal,
            "investment_options": investment_options,
            "strategy": strategy
        }
    
    def process_feedback(self, feedback: str, structured_goal: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user feedback on the recommended strategy.
        
        Args:
            feedback: The user's feedback
            structured_goal: The original structured goal
            strategy: The recommended investment strategy
            
        Returns:
            A dictionary containing the feedback analysis
        """
        logger.info(f"Processing feedback: {feedback}")
        
        # Reset the chat
        self.group_chat.messages = []
        
        # Send the feedback to the feedback agent
        self.user_proxy.send(
            message=f"""
            Process this feedback on an investment recommendation:
            
            Original Goal: {json.dumps(structured_goal)}
            Recommended Strategy: {json.dumps(strategy)}
            User Feedback: {feedback}
            """,
            recipient=self.feedback_agent
        )
        
        analysis = self._wait_for_json_response(self.feedback_agent)
        
        return analysis
    
    def _wait_for_json_response(self, agent: Agent) -> Dict[str, Any]:
        """Wait for a JSON response from an agent."""
        # Get the last message from the agent
        messages = [msg for msg in self.group_chat.messages if msg["sender"]["name"] == agent.name]
        
        if not messages:
            raise ValueError(f"No messages from {agent.name}")
        
        last_message = messages[-1]["content"]
        
        # Extract the JSON object
        try:
            # Find the first '{' and the last '}'
            json_start = last_message.find('{')
            json_end = last_message.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = last_message[json_start:json_end]
                return json.loads(json_str)
            else:
                logger.error(f"Failed to extract JSON from response: {last_message}")
                # Return a default structure
                return {}
        
        except Exception as e:
            logger.error(f"Error extracting JSON: {e}")
            return {}

def present_results(strategy: Dict[str, Any]) -> str:
    """Format the investment strategy for presentation."""
    result_message = f"🔹 Investment Strategy Recommendation 🔹\n\n"
    
    if "description" in strategy:
        result_message += f"{strategy['description']}\n\n"
    
    if "allocation" in strategy:
        result_message += "Recommended Asset Allocation:\n"
        for asset, percentage in strategy["allocation"].items():
            result_message += f"• {asset}: {percentage}%\n"
        result_message += "\n"
    
    if "products" in strategy:
        result_message += "Recommended Investment Products:\n"
        for product in strategy["products"]:
            result_message += f"• {product['name']}: {product['description']}\n"
        result_message += "\n"
    
    if "rationale" in strategy:
        result_message += f"Rationale:\n{strategy['rationale']}\n\n"
    
    result_message += "Would you like to provide feedback on this recommendation?"
    
    return result_message

def main():
    parser = argparse.ArgumentParser(description='Investment Strategy Advisor')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    args = parser.parse_args()
    
    # Initialize the advisor
    advisor = InvestmentStrategyAdvisor()
    
    if args.interactive:
        print("Welcome to the Investment Strategy Advisor!")
        print("Please describe your investment goals (e.g., 'I want to invest for retirement with low risk').")
        print("Type 'quit' to exit.")
        
        while True:
            user_input = input("\nYour investment goal: ")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Thank you for using the Investment Strategy Advisor!")
                break
            
            if user_input.strip():
                # Process the user input
                try:
                    result = advisor.process_user_input(user_input)
                    
                    # Present the results
                    print("\n" + "=" * 80)
                    print(present_results(result["strategy"]))
                    print("=" * 80)
                    
                    # Ask for feedback
                    feedback = input("\nWhat do you think of this recommendation? ")
                    
                    if feedback.strip():
                        # Process the feedback
                        analysis = advisor.process_feedback(
                            feedback,
                            result["structured_goal"],
                            result["strategy"]
                        )
                        
                        print("\nThank you for your feedback! Your preferences have been updated.")
                        print("Would you like to see another investment strategy? Please provide a new goal.")
                except Exception as e:
                    print(f"Error processing your request: {e}")
                    print("Please try again with a clearer investment goal.")
    else:
        # Process a single input from command line
        user_input = input("Please describe your investment goal: ")
        
        if user_input.strip():
            try:
                result = advisor.process_user_input(user_input)
                print(present_results(result["strategy"]))
            except Exception as e:
                print(f"Error processing your request: {e}")

if __name__ == "__main__":
    main()