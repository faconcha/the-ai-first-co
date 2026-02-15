from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared import llm_config


@CrewBase
class CopywriterCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def copywriter(self) -> Agent:
        return Agent(
            config=self.agents_config["copywriter"],
            llm=llm_config.get_llm("creative"),
            verbose=True,
        )

    @task
    def write_content(self) -> Task:
        return Task(
            config=self.tasks_config["write_content"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
