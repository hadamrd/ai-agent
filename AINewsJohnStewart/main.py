import os  
from dotenv import load_dotenv  
from autogen import GroupChat, GroupChatManager  
from AINewsJohnStewart.agents.voice_actor import VoiceActorAgent
from AINewsJohnStewart.agents.scout import ScoutAgent  
from AINewsJohnStewart.agents.satirist import SatiristAgent  
from utils.logger import setup_logger  

load_dotenv()  
logger = setup_logger()  

def main():
    try:
        # Initialize agents with clear roles
        scout = ScoutAgent()
        satirist = SatiristAgent()
        voice_actor = VoiceActorAgent()

        # Configure hierarchical chat
        groupchat = GroupChat(
            agents=[scout, satirist, voice_actor],
            messages=[],
            max_round=8,  # Scout → Satirist → VoiceActor
            speaker_selection_method="round_robin"  # Simple turn-based
        )
        
        manager = GroupChatManager(
            groupchat=groupchat,
            llm_config={"timeout": 45}
        )

        # Initiate workflow with structured data request
        scout.send(
            {
                "request_type": "news_scrape",
                "parameters": {
                    "query": "AI hype",
                    "max_articles": 5
                }
            },
            manager,
            request_reply=True
        )

        # Post-process audio file
        final_message = groupchat.messages[-1]
        if "audio_file" in final_message:
            logger.info(f"Final output: {final_message['audio_file']}")
            
    except Exception as e:
        logger.error(f"Fatal workflow error: {str(e)}")

if __name__ == "__main__":  
    main()  