from mdproc.core import _normalize_tags_field
import sys
sys.path.insert(0, 'src')

result = _normalize_tags_field('adjective/participle')
print(f'Input: adjective/participle')
print(f'Output: {repr(result)}')

# Debug step by step
value = 'adjective/participle'
print(f'Original: {value}')

# Check if / is in punctuation list
punctuation = r'(),:;=\-*\-+.`~"\'?><|\[\]{}\\'
print(f'/ in punctuation: {"/" in punctuation}')

# Manual test
test_value = value
for char in punctuation:
    test_value = test_value.replace(char, ' ')
print(f'After punctuation replacement: {repr(test_value)}')

# Add / to see what happens
test_value2 = value.replace('/', ' ')
print(f'After replacing /: {repr(test_value2)}')
