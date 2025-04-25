# Import autogen
import autogen
from autogen import AssistantAgent, UserProxyAgent


def get_goal_creator_agent(config_list):
    goal_creator = AssistantAgent(
            name="GoalCreatorAgent",
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
    
    return goal_creator