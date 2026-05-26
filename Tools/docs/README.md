# Documentation Directory

This directory contains project documentation and specifications.

## Files

### `requirements.md`
Functional and technical requirements for the German vocabulary processing system. Includes detailed specifications for field normalization, tag management, and processing workflows.

### `test_preprocess.md`  
Test specifications and preprocessing documentation. Contains test cases and validation criteria for the vocabulary processing pipeline.

## Related Documentation

### Requirement Documents
The complete requirement specifications are located in the parent `Requirement/` directory:

- **Requirement 1**: `Requirement 1 - German new words prompt.md`
  - Creating enriched vocabulary entries from raw word lists
  - Templates for nouns, verbs, and other parts of speech
  - Linguistic validation rules

- **Requirement 2**: `Requirement 2 - Normalize Vocabulary Fields and Extract Word List.md`
  - Field normalization procedures using mdproc
  - Word list extraction and deduplication
  - Quality assurance checks

- **Requirement 3**: `Requirement NW3 - Merge see_also Cross-References into Final Vocabulary Database.md`
  - Cross-reference merging workflow
  - See-also field integration
  - Final database generation

- **Requirement 4**: `Requirement 4 - Validate and Normalize see_also Anki References.md` 
  - Anki reference syntax validation
  - Canonical format requirements
  - Normalization procedures

## Usage

These documents provide the complete specification for understanding and implementing the German vocabulary processing system. They should be consulted when:

- Understanding system requirements
- Implementing new features
- Debugging processing issues  
- Validating output quality
- Extending the system functionality

## Format Standards

All documentation follows Markdown format with:
- Clear section headers
- Code examples in appropriate syntax highlighting
- Numbered procedures and checklists
- Cross-references between related documents