# Anthropic Prompt Engineering: Core Techniques

## 1. XML Structure

XML tags serve three functions: separation, reference, and instruction.

**Separation**: Prevent Claude from conflating instructions with data.
```xml
<data>{{RAW_INPUT}}</data>
<instructions>Analyze the data above...</instructions>
```

**Reference**: Name tags, then reference them in natural language.
```xml
Using the contract in <contract> tags, identify indemnification clauses.
<contract>{{CONTRACT_TEXT}}</contract>
```

**Instruction-as-tag**: The tag name itself commands action.
```xml
<prioritize_security_over_convenience>
When trade-offs arise between security and UX, choose security.
Document the trade-off in comments.
</prioritize_security_over_convenience>
```

This pattern enables progressive disclosure: tag name states the rule, contents elaborate.

## 2. Contrastive Examples

Show what NOT to do before what TO do. From Contrastive CoT research: providing invalid demonstrations alongside valid ones improves reasoning accuracy.

```xml
<formatting_rules>
WRONG: "Here's what I found:" followed by unstructured prose
RIGHT: Structured output matching the requested schema, no preamble

WRONG: {"items": ["thing 1", "thing 2"]} with made-up data
RIGHT: {"items": []} when no items found — empty, not fabricated
</formatting_rules>
```

## 3. Specificity Over Abstraction

Concrete parameters outperform vague guidance.

| Vague | Concrete |
|-------|----------|
| "use clear variable names" | "use snake_case, 2-4 words, noun for data, verb for functions" |
| "be concise" | "max 3 sentences per explanation, no preamble" |
| "handle errors appropriately" | "on error: log to stderr, return null, never throw" |

## 4. Output Format Control

**Prefill** the assistant response to bypass preamble and enforce structure:
```
User: Classify this feedback: {{TEXT}}
Assistant: {"sentiment":"
```
Claude continues from the prefill, maintaining the JSON structure.

**Constrain with examples**: Show exact output shape.
```xml
<output_format>
Input: "Great product but shipping was slow"
Output: {"sentiment": "mixed", "pos": ["product quality"], "neg": ["shipping speed"]}

Now process: {{NEW_INPUT}}
</output_format>
```

## 5. Long Context (20K+ tokens)

**Placement**: Documents at TOP, query at BOTTOM. ~30% improvement on complex multi-document tasks.

**Structure**:
```xml
<documents>
  <document index="1">
    <source>report.pdf</source>
    <document_content>{{CONTENT}}</document_content>
  </document>
</documents>

Analyze the documents above. First, quote relevant passages in <quotes>, then answer.
```

**Grounding**: "Quote relevant passages first" forces attention to source material before synthesis.

## 6. Clarity Checklist

- State task purpose and success criteria upfront
- Use numbered steps for procedures
- If you can't explain what the prompt should do, the LLM won't understand either
