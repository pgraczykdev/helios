"""Wyjątki domenowe dla modułu agenta AI w platformie Helios."""


class AgentError(Exception):
    """Bazowy wyjątek domenowy agenta AI."""
    pass


class AgentQuotaExceededError(AgentError):
    """Wyjątek rzucany przy wyczerpaniu limitu tokenów lub zapytań (HTTP 429)."""
    pass


class AgentServiceUnavailableError(AgentError):
    """Wyjątek rzucany przy niedostępności usługi Gemini (HTTP 500/503)."""
    pass


class AgentResponseValidationError(AgentError):
    """Wyjątek rzucany przy pustej lub niepoprawnej odpowiedzi modelu."""
    pass
