from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource

from shared import llm_config

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge"


def _load_knowledge_files() -> list:
    sources = []
    for filepath in sorted(KNOWLEDGE_DIR.glob("*.md")):
        content = filepath.read_text()
        sources.append(StringKnowledgeSource(content=content))
    return sources


@CrewBase
class StrategistCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def content_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["content_strategist"],
            llm=llm_config.get_llm("smart"),
            knowledge_sources=_load_knowledge_files(),
            verbose=True,
        )

    @task
    def create_strategy(self) -> Task:
        return Task(
            config=self.tasks_config["create_strategy"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
