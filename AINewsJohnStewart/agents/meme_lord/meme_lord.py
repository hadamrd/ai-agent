from autogen import AssistantAgent
from openai import OpenAI  

class MemeLordAgent(AssistantAgent):  
    def __init__(self):  
        super().__init__(  
            name="MemeLord",  
            system_message="You create absurd images for each scene. Style: Hyperdank meme. Add Shrek or Elon if possible.",  
            llm_config={"config_list": [...]}  
        )  

    def generate_image(self, scene_description):  
        client = OpenAI()  
        response = client.images.generate(  
            model="dall-e-3",  
            prompt=f"Satirical AI news scene: {scene_description}. Style: meme, exaggerated, 4K, cinematic",  
            size="1024x1024"  
        )  
        return response.data[0].url  
