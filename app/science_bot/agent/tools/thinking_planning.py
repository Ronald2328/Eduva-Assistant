import logfire
from langchain_core.tools import tool  # type: ignore
from pydantic import BaseModel, Field


class ThinkingPlanningSchema(BaseModel):
    """Schema for thinking and planning process.

    CRITICAL: Use this tool to analyze the user's question BEFORE responding.
    This prevents ambiguous responses and ensures proper clarification when needed.

    Key considerations:
    - Is the user's question clear or ambiguous?
    - Do I need more context (school, specific type of process, etc.)?
    - Which tool should I call next (search_documents)?
    - Should I ask for clarification before searching?
    - Are there multiple possible interpretations?
    - CRITICAL: Did search_documents return a message saying "need to ask the user which school"?
      → If YES: Plan to ask user for school immediately

    Examples of ambiguity to detect:
    - "código" → Academic code (MA3536 for a course) or payment code (for bank transaction)?
    - "código del curso" → Which course? Which school?
    - "requisitos para graduarme" → Egresante, Egresado, Bachiller, or Titulado?
    - "costos de trámites" → Which specific process?
    - "información sobre mi carrera" → Which school? What specific info?

    DETECTING WHEN TO ASK FOR SCHOOL:
    - After calling search_documents, if the result message contains "need to ask the user which school"
      → This is a CLEAR SIGNAL to ask: "¿De qué escuela eres?" (in user's language)
    - Remember: search WITHOUT school first, only ask for school when tool explicitly indicates it
    """

    question_analysis: str = Field(
        description=(
            "Analyze the user's question: "
            "Is it clear? Is it ambiguous? What is the user really asking?"
        )
    )

    next_steps: list[str] = Field(
        description=(
            "Planned next steps in order. "
            "Examples: "
            "['Ask user for school', 'Search documents with school parameter'] OR "
            "['Search general documents first', 'If tool says need school, ask user for school'] OR "
            "['Ask clarification about type of code', 'Then search with specific query'] OR "
            "AFTER tool result: ['Tool said need school context', 'Ask: ¿De qué escuela eres?', 'Search again with school']"
        )
    )

    next_tools: list[str] = Field(
        description=(
            "Which tools to call next and in what order. "
            "Available: ['search_documents', 'none'] "
            "Example: ['search_documents'] or [] if asking clarification first"
        )
    )


@tool("thinking_planning", args_schema=ThinkingPlanningSchema)
async def thinking_planning_tool(
    question_analysis: str,
    next_steps: list[str],
    next_tools: list[str],
) -> str:
    """Think about the user's message and plan next steps to provide accurate responses.

    MANDATORY: Call this tool at the beginning of EVERY user interaction and after each tool result.

    This tool helps you:
    - Analyze if the user's question is clear or ambiguous
    - Detect when clarification is needed BEFORE searching documents
    - Plan which tools to call and in what order
    - Decide on search strategy (general vs school-specific)
    - CRITICAL: Detect when search_documents says "need to ask user which school" → ASK FOR SCHOOL

    Critical use cases:
    - User asks about "código" → Is it academic code or payment code?
    - User asks about "requisitos" → Requirements for what specifically?
    - User asks about "costos" → Cost of which process?
    - User mentions their school → Remember it for future queries
    - search_documents result says "need to ask user which school" → Ask: "¿De qué escuela eres?"

    WORKFLOW AFTER search_documents FAILURE:
    1. Read the tool result message carefully
    2. If message contains "need to ask the user which school" → Plan to ask user for school
    3. Ask user directly: "¿De qué escuela eres?" (no preambles, no options)
    4. Once user provides school, search again with school parameter

    Returns:
        Confirmation that planning is complete
    """
    logfire.info(
        "Thinking planning executed",
        question_analysis=question_analysis,
        next_steps=next_steps,
        next_tools=next_tools,
    )

    return "Thinking and planning completed. Proceed with planned steps."


# Export for use in graph
THINKING_TOOL = thinking_planning_tool
