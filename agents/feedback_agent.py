# Import autogen
import autogen
from autogen import AssistantAgent, UserProxyAgent


def get_feedback_agent(config_list):
     # Create the feedback agent - Human Reflection pattern
    feedback_agent = AssistantAgent(
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

    return feedback_agent