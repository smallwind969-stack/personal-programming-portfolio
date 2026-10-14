from app.enterprise_knowledge.service import EnterpriseKnowledgeService
from app.enterprise_knowledge.usage import EnterpriseKnowledgeUsageService
from app.research_reports.runtime import research_report_service
from app.services.experiment_file_service import experiment_file_service
from app.services.experiment_service import experiment_service


enterprise_knowledge_service = EnterpriseKnowledgeService(
    store=experiment_file_service.store,
    report_source=research_report_service,
    workspace_source=experiment_service,
)
enterprise_knowledge_usage_service = EnterpriseKnowledgeUsageService(
    store=experiment_file_service.store,
    knowledge_source=enterprise_knowledge_service,
)
