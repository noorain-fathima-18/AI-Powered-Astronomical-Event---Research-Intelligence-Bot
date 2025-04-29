from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import time
import os
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import base64
from fpdf import FPDF

app = FastAPI(
    title="Astronomy Intelligence Bot API",
    description="API for generating astronomy reports using CrewAI",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ReportRequest(BaseModel):
    topic: str
    temperature: float = 0.7
    process_type: str = "hierarchical"  # or "sequential"

class ReportResponse(BaseModel):
    task_id: str
    status: str = "processing"

class ReportResult(BaseModel):
    topic: str
    report_text: str
    status: str = "completed"
    pdf_base64: Optional[str] = None

# In-memory storage for report results
# In production, use a database
report_tasks = {}

# Set API key
os.environ["OPENAI_API_KEY"] = "sk-..."

# Create PDF from report text
def create_pdf(report_text, topic):
    pdf = FPDF()
    pdf.add_page()
    
    # Set up the PDF
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"Astronomy Intelligence Report: {topic}", ln=True, align="C")
    pdf.ln(10)
    
    # Add timestamp
    pdf.set_font("Arial", "I", 10)
    pdf.cell(190, 10, f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(10)
    
    # Add report content
    pdf.set_font("Arial", "", 12)
    
    # Split the text into paragraphs and add them to the PDF
    paragraphs = report_text.split('\n\n')
    for paragraph in paragraphs:
        if paragraph.strip():
            # Check if this is a heading (starts with # or ## or **)
            if paragraph.startswith('#') or paragraph.startswith('**'):
                pdf.set_font("Arial", "B", 14)
                # Remove the markdown formatting
                clean_para = paragraph.replace('#', '').replace('*', '').strip()
                pdf.cell(190, 10, clean_para, ln=True)
                pdf.set_font("Arial", "", 12)
            else:
                # Handle long text with multicell
                pdf.multi_cell(190, 10, paragraph)
                pdf.ln(5)
    
    pdf_data = pdf.output(dest="S").encode("latin1")
    return base64.b64encode(pdf_data).decode('utf-8')

# Function to run the crew
def run_astronomy_crew(topic, temperature=0.7, process_type="hierarchical"):
    try:
        # LLM setup
        llm_model = "gpt-4o"
        manager_model = "gpt-4o"
        llm = ChatOpenAI(model=llm_model, temperature=temperature)
        
        # Define agents
        space_research_searcher = Agent(
            role="Astronomy Research Specialist",
            goal=f"Find and summarize recent astronomical discoveries and events related to {topic}",
            backstory="You are an expert in astronomy, always up to date with the latest news and findings.",
            llm=llm,
            verbose=True
        )

        observatory_scraper = Agent(
            role="Observatory Data Analyst",
            goal=f"Analyze the latest data from observatories like NASA and ESA about {topic}",
            backstory="You analyze data from observatories and space agencies to identify important updates.",
            llm=llm,
            verbose=True
        )

        research_paper_analyst = Agent(
            role="Astronomical Research Paper Analyst",
            goal=f"Analyze recent astronomy research papers about {topic} and summarize key insights",
            backstory="You specialize in reading and understanding complex astronomy research papers.",
            llm=llm,
            verbose=True
        )

        astro_report_generator = Agent(
            role="Astronomy News Reporter",
            goal=f"Generate a comprehensive report on {topic} based on all gathered data",
            backstory="You write astronomy reports for scientists and enthusiasts.",
            llm=llm,
            verbose=True
        )
        
        # Define tasks
        task1 = Task(
            description=(
                f"Find the latest discoveries and information about {topic} in astronomy. "
                f"Include recent findings, important developments, and upcoming events if relevant."
            ),
            agent=space_research_searcher,
            expected_output=f"Detailed list of recent astronomical discoveries and information related to {topic}."
        )

        task2 = Task(
            description=(
                f"Collect data from NASA, ESA, and other reputable space observatories about {topic}. "
                f"Include mission data, telescope observations, and other relevant information."
            ),
            agent=observatory_scraper,
            context=[task1],
            expected_output=f"Summarized data from observatories about {topic}."
        )

        task3 = Task(
            description=(
                f"Analyze recent research papers about {topic} focusing on the findings and observations mentioned earlier. "
                f"Summarize key insights understandable to the public and experts."
            ),
            agent=research_paper_analyst,
            context=[task2],
            expected_output=f"Summarized key findings from recent research papers about {topic}."
        )

        task4 = Task(
            description=(
                f"Compile a final, comprehensive report on {topic} incorporating all findings, discoveries, research insights, "
                f"and observatory data. The report should be detailed and informative for enthusiasts and experts alike."
            ),
            agent=astro_report_generator,
            context=[task1, task2, task3],
            expected_output=f"Final intelligence report about {topic} summarizing all findings in detail."
        )
        
        # Set up the crew
        manager_llm = ChatOpenAI(model=manager_model, temperature=temperature)
        
        # Map process type string to enum
        process_enum = Process.hierarchical if process_type.lower() == "hierarchical" else Process.sequential
        
        astro_crew = Crew(
            agents=[space_research_searcher, observatory_scraper, research_paper_analyst, astro_report_generator],
            tasks=[task1, task2, task3, task4],
            manager_llm=manager_llm,
            process=process_enum,
            verbose=True
        )
        
        # Run the crew
        result = astro_crew.kickoff(inputs={"topic": topic})
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

# Background task to generate report
async def generate_report_task(task_id, topic, temperature, process_type):
    try:
        # report_text = run_astronomy_crew(topic, temperature, process_type)

        crew_output = run_astronomy_crew(topic, temperature, process_type)
        report_text = str(crew_output)
        pdf_base64 = create_pdf(report_text, topic)
        
        report_tasks[task_id] = {
            "topic": topic,
            "report_text": report_text,
            "status": "completed",
            "pdf_base64": pdf_base64
        }
    except Exception as e:
        report_tasks[task_id] = {
            "topic": topic,
            "report_text": f"Error generating report: {str(e)}",
            "status": "failed"
        }

@app.post("/generate-report", response_model=ReportResponse)
async def start_report_generation(report_request: ReportRequest, background_tasks: BackgroundTasks):
    task_id = f"task_{int(time.time())}"
    report_tasks[task_id] = {"status": "processing"}
    
    background_tasks.add_task(
        generate_report_task,
        task_id=task_id,
        topic=report_request.topic,
        temperature=report_request.temperature,
        process_type=report_request.process_type
    )
    
    return {"task_id": task_id, "status": "processing"}

@app.get("/report/{task_id}", response_model=ReportResult)
async def get_report(task_id: str):
    if task_id not in report_tasks:
        raise HTTPException(status_code=404, detail="Report not found")
    
    task_data = report_tasks[task_id]
    
    if task_data["status"] == "processing":
        return {"topic": "", "report_text": "", "status": "processing"}
    
    return task_data

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
