"""
FILE: backend/src/aura/llm/structured.py
PURPOSE: Convert closed Pydantic schemas to strict provider response schemas.
MAIN RESPONSIBILITY: Structured Output Schemas.
INPUTS: JSON-schema dictionary.
OUTPUTS: Copied strict schema or rejection of open dictionaries.
IMPORTANT FUNCTIONS / CLASSES: strict_schema.
CONNECTED MODULES: See imports below for local and external dependencies.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "Structured JSON improves format reliability; it does not establish factual correctness."
"""
# PRESENTATION SECTION: STRUCTURED OUTPUT SCHEMAS
from copy import deepcopy


def strict_schema(schema):
    """Purpose: Structured response schemas.
    
    Inputs: Pydantic JSON-schema dictionary.
    Process and rationale: Deep-copy schema, disallow extra properties, require declared fields and reject open dictionaries for strict output.
    Returns: Adapted schema without mutating its input.
    """
    result=deepcopy(schema)
    def visit(node):
        if isinstance(node,list):
            for value in node:visit(value)
        elif isinstance(node,dict):
            node.pop('default',None)
            if node.get('type')=='object':
                if node.get('additionalProperties') not in (False,None):
                    raise ValueError('Open dictionaries cannot use strict output')
                node['additionalProperties']=False
                node['required']=list(node.get('properties',{}))
            for value in node.values():visit(value)
    visit(result)
    return result
