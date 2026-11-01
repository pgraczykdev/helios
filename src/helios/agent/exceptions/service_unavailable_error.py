from helios.agent.exceptions.agent_error import AgentError


class AgentServiceUnavailableError(AgentError):
    """Exception raised when the Gemini API service is unavailable (HTTP 500/503)."""

    pass
