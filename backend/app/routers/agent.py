from fastapi import APIRouter
from app.services.agent_langchain import handle_analytics_question
from app.schemas.dto import AgentRequest, AgentResponse

router = APIRouter()

@router.post("/agent", response_model=AgentResponse)
def agent_endpoint(req: AgentRequest):
    """
    Endpoint que usa LangChain para entender a pergunta
    e consultar o Firestore via funções existentes.
    """
    answer, intent = handle_analytics_question(req.question)
    return AgentResponse(answer=answer, intent=intent)
