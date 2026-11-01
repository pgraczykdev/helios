from helios.agent.exceptions.agent_error import AgentError


class AgentQuotaExceededError(AgentError):
    """Exception raised when API token or request quota is exhausted (HTTP 429)."""

    pass
