from helios.agent.exceptions.agent_error import AgentError


class AgentServiceUnavailableError(AgentError):
    """Wyjątek rzucany przy niedostępności usługi Gemini (HTTP 500/503)."""

    pass
