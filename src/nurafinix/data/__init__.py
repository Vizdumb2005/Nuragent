"""Sample data for the Nurafinix Prospect Engine."""

SAMPLE_CSV = """name,website,description,category,size,location,source_url
Acme Corp,https://www.acme.com,"A tech company looking for data solutions","Data,SQL,Python",100-200,San Francisco,https://www.acme.com
TechStart Inc,https://techstart.com,"Startup needing analytics help","Analytics,Dashboard",10-50,Austin,https://techstart.com
DataFlow Ltd,https://dataflow.example,"Data engineering company","Data Engineering,AI",50-100,New York,https://dataflow.example
WebSolutions Co,https://websolutions.biz,"Web development agency","Web Development,Integrations",200-500,Seattle,https://websolutions.biz
Automation Inc,https://automation.io,"Looking to automate processes","Automation,Workflow",50-100,Boston,https://automation.io
"""

SAMPLE_CANDIDATES = [
    {
        "name": "Acme Corp",
        "website": "https://www.acme.com",
        "description": "A tech company looking for data solutions",
        "categories": ["data_analytics", "sql_python_reporting"],
        "size": "100-200",
        "location": "San Francisco",
    },
    {
        "name": "TechStart Inc",
        "website": "https://techstart.com",
        "description": "Startup needing analytics help",
        "categories": ["data_analytics"],
        "size": "10-50",
        "location": "Austin",
    },
    {
        "name": "DataFlow Ltd",
        "website": "https://dataflow.example",
        "description": "Data engineering company",
        "categories": ["data_engineering", "ai_ml_engineering"],
        "size": "50-100",
        "location": "New York",
    },
]
