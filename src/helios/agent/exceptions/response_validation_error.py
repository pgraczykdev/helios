from helios.agent.exceptions.agent_error import AgentError


class AgentResponseValidationError(AgentError):
    """Exception raised when the model returns an empty or unparsable response."""

    pass
