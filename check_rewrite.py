import sys
sys.path.insert(0, ".")
from pro_implementation.answer import rewrite_query

question = "What innovation does Radixweb do?"
rewritten = rewrite_query(question, [])
print(f"Original: {question}")
print(f"Rewritten: {rewritten}")
