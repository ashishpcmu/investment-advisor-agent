# Import autogen
import autogen
from autogen import AssistantAgent, UserProxyAgent


def get_presentation_agent(config_list):
    presentation_agent = AssistantAgent(
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

    return presentation_agent