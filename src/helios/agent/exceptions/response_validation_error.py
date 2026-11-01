from helios.agent.exceptions.agent_error import AgentError


class AgentResponseValidationError(AgentError):
    """Wyjątek rzucany przy pustej lub niepoprawnej odpowiedzi modelu."""

    pass
