from helios.agent.exceptions.agent_error import AgentError


class AgentQuotaExceededError(AgentError):
    """Wyjątek rzucany przy wyczerpaniu limitu tokenów lub zapytań (HTTP 429)."""

    pass
