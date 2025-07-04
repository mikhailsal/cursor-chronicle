# Test Suite Documentation

This directory contains comprehensive tests for Cursor Chronicle.

## Test Types

### Unit Tests (`test_cursor_chronicle.py`)
- Basic functionality tests with mocked/controlled data
- Test individual methods and components
- Fast execution, no external dependencies

### Integration Tests (`test_integration.py`)
- **Real database integration** - uses actual local Cursor databases
- **No mocks** - tests against real data and file system
- **Resilient design** - works regardless of database state
- **Comprehensive coverage** - tests all major functionality paths

## Integration Test Features

### Database Independence
- Tests work whether Cursor databases exist or not
- Graceful handling of missing/corrupted databases
- Validates behavior with empty results

### Real-World Scenarios
- Tests with actual project data (if available)
- Verifies formatting with real message structures
- Validates tool call processing with actual data

### Edge Case Coverage
- Missing database files
- Corrupted JSON data
- Malformed database entries
- Missing required fields
- Invalid input parameters

### No-Crash Guarantee
- All tests designed to verify "no crashes" rather than specific outputs
- Validates return types and basic structure
- Ensures graceful error handling

## Running Tests

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run specific test file
python -m pytest tests/test_integration.py -v
```

## Test Philosophy

The integration tests follow these principles:

1. **Real Data**: Use actual Cursor databases when available
2. **No Assumptions**: Don't assume specific data exists
3. **Crash Prevention**: Primary goal is ensuring no exceptions
4. **Type Safety**: Verify return types and basic structure
5. **Edge Case Resilience**: Handle all possible database states

## Coverage

Current test coverage: ~72% of codebase
- High coverage of core functionality
- Integration tests exercise real-world usage patterns
- Unit tests cover edge cases and utility functions 