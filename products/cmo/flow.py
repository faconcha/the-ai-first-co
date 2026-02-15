import datetime
from pathlib import Path

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

from shared import settings
from products.cmo.crews.strategist.strategist_crew import StrategistCrew
from products.cmo.crews.copywriter.copywriter_crew import CopywriterCrew


class CMOFlowState(BaseModel):
    topic: str = ""
    audience: str = ""
    platform: str = "linkedin"
    language: str = "en"
    company_name: str = ""
    company_product: str = ""
    company_voice: str = ""
    strategy: str = ""
    content: str = ""


class CMOFlow(Flow[CMOFlowState]):

    @start()
    def load_context(self):
        company = settings.get_company_config()
        self.state.company_name = company["name"]
        self.state.company_product = company["product"]
        self.state.company_voice = company["voice"]

    @listen(load_context)
    def create_strategy(self):
        inputs = {
            "topic": self.state.topic,
            "audience": self.state.audience,
            "platform": self.state.platform,
            "language": self.state.language,
            "company_name": self.state.company_name,
            "company_product": self.state.company_product,
            "company_voice": self.state.company_voice,
        }
        result = StrategistCrew().crew().kickoff(inputs=inputs)
        self.state.strategy = result.raw

    @listen(create_strategy)
    def write_content(self):
        inputs = {
            "strategy": self.state.strategy,
            "platform": self.state.platform,
            "language": self.state.language,
            "company_name": self.state.company_name,
            "company_product": self.state.company_product,
            "company_voice": self.state.company_voice,
        }
        result = CopywriterCrew().crew().kickoff(inputs=inputs)
        self.state.content = result.raw

    @listen(write_content)
    def save_output(self):
        output_dir = settings.ensure_output_dir("cmo")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.state.platform}_{timestamp}.md"
        filepath = output_dir / filename

        with open(filepath, "w") as f:
            f.write(self.state.content)

        return str(filepath)
