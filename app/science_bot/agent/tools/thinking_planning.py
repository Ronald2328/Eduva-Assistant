import logfire
from langchain_core.tools import tool  # type: ignore
from pydantic import BaseModel, Field


class ThinkingPlanningSchema(BaseModel):
    """Schema for thinking and planning process.

    CRITICAL: Use this tool to analyze the user's question BEFORE responding.
    This prevents ambiguous responses and ensures proper clarification when needed.

    STEP 0 - CLASSIFY QUERY TYPE:
    - ACADEMIC CONTENT: Questions about courses, cycles, credits, academic codes, study plan, curriculum
      → Always search directly. NEVER ask about costs. NEVER apply trámite segmentation.
      → Examples: "ciclo del álgebra lineal", "créditos de física II", "código del curso de estadística"
    - ADMINISTRATIVE: Questions about procedures, enrollment, graduation, transfers, validation
      → Apply segmentation and ambiguity detection.
      → Examples: "costo de matrícula", "requisitos para graduarme", "proceso de convalidación"

    CRITICAL: ALWAYS SEARCH, NEVER ASSUME FROM HISTORY
    - Even if a similar question was answered before, ALWAYS call search_documents again
    - Conversation history = only for school context. NOT a fact source.

    Key considerations:
    - What TYPE is this query? (ACADEMIC CONTENT or ADMINISTRATIVE?)
    - If ACADEMIC CONTENT → search_documents directly, no cost questions
    - If ADMINISTRATIVE → Is it clear or ambiguous?
    - Do I need more context (school, specific type of process, etc.)?
    - CRITICAL: Did search_documents return a message saying "need to ask the user which school"?
      → If YES: Plan to ask user for school immediately

    Examples of ambiguity to detect (ADMINISTRATIVE ONLY):
    - "código de pago" vs "código académico" → only ambiguous when context is truly unclear
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
            "FIRST classify: is this ACADEMIC CONTENT (courses/cycles/credits/plan de estudios) "
            "or ADMINISTRATIVE (trámite/costo/requisito/proceso)? "
            "Then: Is it clear? Is it ambiguous? What is the user really asking? "
            "ACADEMIC CONTENT → never ask about costs, search directly. "
            "ADMINISTRATIVE → check for ambiguity before searching."
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
