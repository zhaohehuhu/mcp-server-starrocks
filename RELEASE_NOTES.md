# StarRocks MCP Server Release Notes

## Version 0.4.0

### Enhancements

1. **Upgrade FastMCP to 2.14+** (commit e21bcd9)
   - Bumped fastmcp dependency requirement from `>=2.12.0,<2.13.0` to `>=2.14.0`
   - Picks up upstream improvements and bug fixes from the FastMCP framework

2. **Support `use_pure` connection parameter** (commit 65398d1)
   - Added new `STARROCKS_USE_PURE` environment variable
   - Passes through to mysql.connector's `use_pure` connection parameter
   - Allows users to force the pure-Python MySQL implementation when the C extension causes issues
   - Defaults to `false`; accepts `true`, `1`, or `yes` (case-insensitive) to enable

3. **macOS Keychain-backed password lookup** (commits ac33aec, f847013, PR #39)
   - `STARROCKS_PASSWORD` now accepts a `keychain:<service>[/<account>]` reference, resolved via the macOS `security` CLI at connection time
   - Keeps credentials out of environment variables, shell history, and process listings on macOS
   - Lookup is deferred until the first connection, so a missing keychain entry only fails when actually connecting
   - Thanks to @yakirgb for the contribution

### Bug Fixes

1. **Fix inconsistency of table_overview row limit description** (commit 9067b9e)
   - Corrected the tool description for `table_overview` to state "up to 3" sample rows, matching the actual behavior (previously documented as "up to 5")

2. **Fix BIGINT precision loss in structured_content JSON serialization** (commit 620bf40, PR #37, fixes #36)
   - Integers exceeding JavaScript's `Number.MAX_SAFE_INTEGER` (2^53-1) are now converted to strings in `ResultSet.to_dict()` so MCP clients no longer silently round large BIGINT values when parsing JSON
   - The text content path (`to_string`) is unaffected
   - Thanks to @mixermt for the contribution

### Breaking Changes

None - this release maintains full backward compatibility with version 0.3.0.

## Version 0.3.0

### Bug Fixes

1. **Fix TypeError in stdio Transport Mode** (commit 58f8b9e, PR #26)
   - Fixed TypeError when running server in 'stdio' mode
   - Removed incorrect host/port parameters passed to run_async() for stdio transport
   - stdio mode no longer requires or accepts host/port configuration
   - Thanks to @nightingale10 for the contribution

2. **Fix STARROCKS_URL Connection Parameter Handling** (commit 249e17b)
   - Fixed error when using STARROCKS_URL with unsupported schema parameter
   - Improved parse_connection_url() to filter out parameters not supported by mysql.connector
   - Removed 'schema' from connection parameters as it's not a valid mysql.connector parameter
   - Now only returns supported connection parameters: user, host, password, port, database
   - Enhanced robustness of connection URL parsing

3. **Fix Database Summary Refresh Logic** (commit 9a6f3f6)
   - Fixed logic bug in db_summary_manager.py that caused refresh to fail
   - Corrected short-circuit evaluation issue in _sync_table_list() call
   - Changed condition from `if refresh or not self._sync_table_list(database)` to `if not self._sync_table_list(database, force=refresh)`
   - Database summary refresh now works correctly when refresh=True is specified

### Testing Updates

- Updated test suite to reflect removal of 'schema' parameter from connection URL parsing
- All existing tests pass with the new connection parameter filtering logic
- Enhanced test coverage for edge cases in connection URL parsing

### Breaking Changes

None - this release maintains full backward compatibility with version 0.2.0. All changes are internal bug fixes that improve reliability and correctness.

## Version 0.2.0

### Major Features and Enhancements

1. **Enhanced STARROCKS_URL Parsing** (commit 80ac0ba)
   - Support for flexible connection URL formats including empty passwords
   - Handle patterns like "root:@localhost:9030" and "root@localhost:9030"
   - Support missing ports with default 9030: "root:password@localhost"
   - Support minimal format: "user@host" with empty password and default port
   - Maintain backward compatibility with existing valid URLs
   - Comprehensive test coverage for edge cases
   - Fixed DBClient to properly convert string port to integer

2. **Connection Health Monitoring** (commit b8a80c6)
   - Added new connection_health_checker.py module
   - Implemented health checking functionality for database connections
   - Enhanced connection reliability and monitoring capabilities
   - Proactive connection health management

3. **Visualization Enhancements** (commit b6f26ec)
   - Added format parameter to query_and_plotly_chart tool
   - Enhanced chart generation capabilities with configurable output formats
   - Improved flexibility for data visualization workflows

### Testing and Infrastructure

- Added comprehensive test coverage for STARROCKS_URL parsing edge cases
- Enhanced test suite with new test cases for database client functionality
- Improved error handling and validation for connection scenarios

### Breaking Changes

None - this release maintains full backward compatibility with version 0.1.5.

## Version 0.1.5

Major Features and Enhancements

1. Connection Pooling and Architecture Refactor (commit 0fc372d)
  - Major refactor introducing connection pooling for improved performance
  - Extracted database client logic into separate db_client.py module
  - Enhanced connection management and reliability
2. Enhanced Arrow Flight SQL Support (commit 877338f)
  - Improved Arrow Flight SQL connection handling
  - Better result processing for high-performance queries
  - Enhanced error handling for Arrow Flight connections
3. New Query Analysis Tools (commit 60ca975)
  - Added collect_query_dump_and_profile functionality
  - Enhanced query performance analysis capabilities
4. Database Summary Management (commits d269ebe, 5b2ca59)
  - Added new db_summary_manager.py module
  - Implemented database summary functionality for better overview capabilities
  - Enhanced database exploration features
5. Configuration Enhancements (commit fb09271)
  - Added STARROCKS_URL configuration option
  - Improved connection configuration flexibility

  Testing and Infrastructure

- Updated test suite with new test cases for database client functionality
- Added comprehensive testing for Arrow Flight SQL features
- Improved test infrastructure with new README documentation

  Breaking Changes

- Major refactor may require configuration updates for some deployment scenarios
- Connection handling has been restructured (though backwards compatibility is maintained)

## Version 0.1.4


## Version 0.1.3

1. refactor using fastmcp
2. add new config STARROCKS_MYSQL_AUTH_PLUGIN

## Version 0.1.2

Fix accidental extra import of sqlalalchemy

## Version 0.1.1

1. add new tool query_and_plotly_chart
2. add new tool table_overview & db_overview
3. add env config STARROCKS_DB and STARROCKS_OVERVIEW_LIMIT, both optional


## Version 0.1.0 (Initial Release)

We are excited to announce the first release of the StarRocks MCP (Model Context Protocol) Server. This server enables AI assistants to interact directly with StarRocks databases, providing a seamless interface for executing queries and retrieving database information.

### Description

The StarRocks MCP Server acts as a bridge between AI assistants and StarRocks databases, allowing for direct SQL execution and database exploration without requiring complex setup or configuration. This initial release provides essential functionality for database interaction while maintaining security and performance.

### Features

- **SQL Query Execution**
  - `read_query` tool for executing SELECT queries and commands that return result sets
  - `write_query` tool for executing DDL/DML statements and other StarRocks commands
  - Proper error handling and connection management

- **Database Exploration**
  - List all databases in a StarRocks instance
  - View table schemas using SHOW CREATE TABLE
  - List all tables within a specific database

- **System Information Access**
  - Access to StarRocks internal system information via proc-like interface
  - Visibility into FE nodes, BE nodes, CN nodes, databases, tables, partitions, transactions, jobs, and more

- **Flexible Configuration**
  - Configurable connection parameters (host, port, user, password)
  - Support for both package installation and local directory execution

### Requirements

- Python 3.10 or higher
- Dependencies:
  - mcp >= 1.0.0
  - mysql-connector-python >= 9.2.0

### Configuration

The server can be configured through environment variables:

- `STARROCKS_HOST` (default: localhost)
- `STARROCKS_PORT` (default: 9030)
- `STARROCKS_USER` (default: root)
- `STARROCKS_PASSWORD` (default: empty)
- `STARROCKS_MYSQL_AUTH_PLUGIN` (default: mysql_native_password) user can also pass different auth plugins like `mysql_clear_password`

### Installation

The server can be installed as a Python package:

```bash
pip install mcp-server-starrocks
```

Or run directly from the source:

```bash
uv --directory path/to/mcp-server-starrocks run mcp-server-starrocks
```

### MCP Integration

Add the following configuration to your MCP settings file:

```json
{
  "mcpServers": {
    "mcp-server-starrocks": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp-server-starrocks",
        "mcp-server-starrocks"
      ],
      "env": {
        "STARROCKS_HOST": "localhost",
        "STARROCKS_PORT": "9030",
        "STARROCKS_USER": "root",
        "STARROCKS_PASSWORD": "",
        "STARROCKS_MYSQL_AUTH_PLUGIN":"mysql_clear_password"
      }
    }
  }
}
```

---

We welcome feedback and contributions to improve the StarRocks MCP Server. Please report any issues or suggestions through our GitHub repository.
