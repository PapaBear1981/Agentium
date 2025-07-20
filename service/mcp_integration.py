"""
MCP (Model Context Protocol) Integration for Jarvis Multi-Agent AI System.

This module provides integration with Smithery MCP registry, McpWorkbench,
and MCPSafetyScanner for dynamic tool installation and management.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import httpx
import structlog
from pydantic import BaseModel

from models.tools import (
    ToolDefinition, ToolRegistry, ToolInstallRequest, ToolInstallResponse,
    ToolExecutionRequest, ToolExecutionResponse, ToolSearchRequest, ToolSearchResponse,
    ToolStatus, ToolSafetyLevel, ToolExecutionStatus, ToolCategory
)

logger = structlog.get_logger(__name__)

class MCPError(Exception):
    """Base exception for MCP-related errors."""
    pass

class ToolInstallationError(MCPError):
    """Exception for tool installation errors."""
    pass

class ToolExecutionError(MCPError):
    """Exception for tool execution errors."""
    pass

class SafetyValidationError(MCPError):
    """Exception for safety validation errors."""
    pass

class SmitheryRegistry:
    """Interface to Smithery MCP registry."""
    
    def __init__(self, registry_url: str = "https://smithery.ai/api/v1"):
        self.registry_url = registry_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_tools(self, request: ToolSearchRequest) -> ToolSearchResponse:
        """Search for tools in the Smithery registry."""
        try:
            params = {
                "q": request.query,
                "category": request.category.value if request.category else None,
                "tags": ",".join(request.tags) if request.tags else None,
                "min_rating": request.min_rating,
                "max_size_mb": request.max_install_size_mb,
                "safety_level": request.safety_level.value if request.safety_level else None,
                "sort_by": request.sort_by,
                "sort_order": request.sort_order,
                "limit": request.limit,
                "offset": request.offset
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            response = await self.client.get(f"{self.registry_url}/tools/search", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to ToolDefinition objects
            tools = []
            for tool_data in data.get("tools", []):
                tools.append(ToolDefinition(
                    name=tool_data["name"],
                    version=tool_data["version"],
                    description=tool_data["description"],
                    category=ToolCategory(tool_data.get("category", "custom")),
                    author=tool_data["author"],
                    license=tool_data["license"],
                    homepage=tool_data.get("homepage"),
                    documentation_url=tool_data.get("documentation_url"),
                    functions=tool_data.get("functions", []),
                    dependencies=tool_data.get("dependencies", []),
                    safety_level=ToolSafetyLevel(tool_data.get("safety_level", "safe")),
                    safety_score=tool_data.get("safety_score", 100),
                    download_count=tool_data.get("download_count", 0),
                    rating=tool_data.get("rating"),
                    tags=tool_data.get("tags", [])
                ))
            
            return ToolSearchResponse(
                tools=tools,
                total_count=data.get("total_count", len(tools)),
                query=request.query,
                search_time_ms=data.get("search_time_ms", 0)
            )
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to search Smithery registry: {e}")
            raise MCPError(f"Registry search failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error searching registry: {e}")
            raise MCPError(f"Search failed: {e}")
    
    async def get_tool_info(self, tool_name: str, version: str = "latest") -> Optional[ToolDefinition]:
        """Get detailed information about a specific tool."""
        try:
            response = await self.client.get(f"{self.registry_url}/tools/{tool_name}/{version}")
            response.raise_for_status()
            
            data = response.json()
            
            return ToolDefinition(
                name=data["name"],
                version=data["version"],
                description=data["description"],
                category=ToolCategory(data.get("category", "custom")),
                author=data["author"],
                license=data["license"],
                homepage=data.get("homepage"),
                documentation_url=data.get("documentation_url"),
                functions=data.get("functions", []),
                dependencies=data.get("dependencies", []),
                safety_level=ToolSafetyLevel(data.get("safety_level", "safe")),
                safety_score=data.get("safety_score", 100),
                download_count=data.get("download_count", 0),
                rating=data.get("rating"),
                tags=data.get("tags", [])
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get tool info: {e}")
            raise MCPError(f"Failed to get tool info: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting tool info: {e}")
            raise MCPError(f"Failed to get tool info: {e}")
    
    async def download_tool(self, tool_name: str, version: str = "latest") -> bytes:
        """Download a tool package."""
        try:
            response = await self.client.get(f"{self.registry_url}/tools/{tool_name}/{version}/download")
            response.raise_for_status()
            
            return response.content
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to download tool: {e}")
            raise ToolInstallationError(f"Download failed: {e}")

class MCPSafetyScanner:
    """Safety scanner for MCP tools."""
    
    def __init__(self):
        self.scan_rules = self._load_scan_rules()
    
    def _load_scan_rules(self) -> Dict[str, Any]:
        """Load safety scanning rules."""
        return {
            "dangerous_imports": [
                "os.system", "subprocess.call", "eval", "exec",
                "open", "__import__", "compile"
            ],
            "suspicious_patterns": [
                r"rm\s+-rf", r"del\s+/", r"format\s+c:",
                r"curl.*\|.*sh", r"wget.*\|.*sh"
            ],
            "required_permissions": [
                "network", "filesystem", "system"
            ],
            "max_file_size_mb": 100,
            "allowed_file_types": [".py", ".js", ".json", ".yaml", ".yml", ".md"]
        }
    
    async def scan_tool(self, tool_content: bytes, tool_name: str) -> Tuple[int, List[str]]:
        """Scan a tool for safety issues."""
        warnings = []
        safety_score = 100
        
        try:
            # Check file size
            size_mb = len(tool_content) / (1024 * 1024)
            if size_mb > self.scan_rules["max_file_size_mb"]:
                warnings.append(f"Tool size ({size_mb:.1f}MB) exceeds limit")
                safety_score -= 20
            
            # Decode content for text analysis
            try:
                content_str = tool_content.decode('utf-8')
            except UnicodeDecodeError:
                warnings.append("Tool contains binary content that cannot be analyzed")
                safety_score -= 10
                return max(0, safety_score), warnings
            
            # Check for dangerous imports
            for dangerous_import in self.scan_rules["dangerous_imports"]:
                if dangerous_import in content_str:
                    warnings.append(f"Contains potentially dangerous import: {dangerous_import}")
                    safety_score -= 15
            
            # Check for suspicious patterns
            import re
            for pattern in self.scan_rules["suspicious_patterns"]:
                if re.search(pattern, content_str, re.IGNORECASE):
                    warnings.append(f"Contains suspicious pattern: {pattern}")
                    safety_score -= 25
            
            # Check for network access
            network_indicators = ["http://", "https://", "socket", "urllib", "requests"]
            if any(indicator in content_str for indicator in network_indicators):
                warnings.append("Tool may access network resources")
                safety_score -= 5
            
            # Check for file system access
            fs_indicators = ["open(", "file(", "pathlib", "os.path", "shutil"]
            if any(indicator in content_str for indicator in fs_indicators):
                warnings.append("Tool may access file system")
                safety_score -= 5
            
            logger.info(f"Safety scan completed for {tool_name}: score={safety_score}, warnings={len(warnings)}")
            
            return max(0, safety_score), warnings
            
        except Exception as e:
            logger.error(f"Safety scan failed for {tool_name}: {e}")
            return 0, [f"Safety scan failed: {e}"]

class McpWorkbench:
    """MCP Workbench for tool management and execution."""
    
    def __init__(self, tools_dir: Path = Path("./mcp_tools")):
        self.tools_dir = tools_dir
        self.tools_dir.mkdir(exist_ok=True)
        self.installed_tools: Dict[str, ToolRegistry] = {}
        self.safety_scanner = MCPSafetyScanner()
    
    async def install_tool(self, request: ToolInstallRequest, registry: SmitheryRegistry) -> ToolInstallResponse:
        """Install a tool from the registry."""
        start_time = time.time()
        install_id = uuid4()
        
        try:
            logger.info(f"Installing tool: {request.tool_name} v{request.version}")
            
            # Get tool information
            tool_info = await registry.get_tool_info(request.tool_name, request.version)
            if not tool_info:
                raise ToolInstallationError(f"Tool not found: {request.tool_name}")
            
            # Download tool
            tool_content = await registry.download_tool(request.tool_name, request.version)
            
            # Safety scan
            if request.run_safety_scan:
                safety_score, warnings = await self.safety_scanner.scan_tool(tool_content, request.tool_name)
                
                if safety_score < 50:
                    raise SafetyValidationError(f"Tool failed safety scan: score={safety_score}")
                
                logger.info(f"Safety scan passed: score={safety_score}, warnings={len(warnings)}")
            else:
                safety_score = 100
                warnings = []
            
            # Install tool
            tool_path = self.tools_dir / f"{request.tool_name}_{request.version}"
            tool_path.mkdir(exist_ok=True)
            
            # Extract and save tool files
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                temp_file.write(tool_content)
                temp_file.flush()
                
                # Extract (assuming zip format)
                import zipfile
                with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                    zip_ref.extractall(tool_path)
            
            # Create registry entry
            tool_registry = ToolRegistry(
                tool_name=request.tool_name,
                version=request.version,
                status=ToolStatus.INSTALLED,
                install_path=str(tool_path),
                config=request.config,
                safety_score=safety_score
            )
            
            self.installed_tools[request.tool_name] = tool_registry
            
            installation_time = int((time.time() - start_time) * 1000)
            
            return ToolInstallResponse(
                tool_name=request.tool_name,
                version=request.version,
                status=ToolStatus.INSTALLED,
                install_id=install_id,
                installation_time_ms=installation_time,
                success=True,
                message=f"Tool {request.tool_name} installed successfully",
                safety_score=safety_score,
                safety_level=tool_info.safety_level,
                safety_warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Tool installation failed: {e}")
            installation_time = int((time.time() - start_time) * 1000)
            
            return ToolInstallResponse(
                tool_name=request.tool_name,
                version=request.version or "latest",
                status=ToolStatus.ERROR,
                install_id=install_id,
                installation_time_ms=installation_time,
                success=False,
                message=f"Installation failed: {e}",
                error_details={"error": str(e), "type": type(e).__name__}
            )
    
    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResponse:
        """Execute a tool function."""
        start_time = time.time()
        
        try:
            if request.tool_name not in self.installed_tools:
                raise ToolExecutionError(f"Tool not installed: {request.tool_name}")
            
            tool_registry = self.installed_tools[request.tool_name]
            
            # Load tool module
            tool_path = Path(tool_registry.install_path)
            
            # Execute tool (simplified - would need proper sandboxing in production)
            result = await self._execute_tool_function(
                tool_path, 
                request.function_name, 
                request.parameters,
                request.sandbox_mode
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Update usage statistics
            tool_registry.usage_count += 1
            tool_registry.success_count += 1
            tool_registry.total_execution_time_ms += execution_time
            tool_registry.avg_execution_time_ms = (
                tool_registry.total_execution_time_ms / tool_registry.usage_count
            )
            
            return ToolExecutionResponse(
                execution_id=request.execution_id,
                tool_name=request.tool_name,
                function_name=request.function_name,
                status=ToolExecutionStatus.COMPLETED,
                result=result,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            # Update failure statistics
            if request.tool_name in self.installed_tools:
                self.installed_tools[request.tool_name].failure_count += 1
            
            return ToolExecutionResponse(
                execution_id=request.execution_id,
                tool_name=request.tool_name,
                function_name=request.function_name,
                status=ToolExecutionStatus.FAILED,
                execution_time_ms=execution_time,
                error=str(e),
                error_code="EXECUTION_ERROR"
            )
    
    async def _execute_tool_function(
        self, 
        tool_path: Path, 
        function_name: str, 
        parameters: Dict[str, Any],
        sandbox_mode: bool = True
    ) -> Any:
        """Execute a specific tool function."""
        # This is a simplified implementation
        # In production, you'd want proper sandboxing and security measures
        
        try:
            # Load the tool's main module
            main_file = tool_path / "main.py"
            if not main_file.exists():
                raise ToolExecutionError("Tool main.py not found")
            
            # Execute in subprocess for basic isolation
            if sandbox_mode:
                cmd = [
                    "python", str(main_file),
                    "--function", function_name,
                    "--parameters", json.dumps(parameters)
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tool_path
                )
                
                if result.returncode != 0:
                    raise ToolExecutionError(f"Tool execution failed: {result.stderr}")
                
                return json.loads(result.stdout) if result.stdout else None
            else:
                # Direct execution (less secure but faster)
                import importlib.util
                spec = importlib.util.spec_from_file_location("tool_module", main_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, function_name):
                    func = getattr(module, function_name)
                    return func(**parameters)
                else:
                    raise ToolExecutionError(f"Function {function_name} not found in tool")
                    
        except Exception as e:
            raise ToolExecutionError(f"Tool execution failed: {e}")
    
    def list_installed_tools(self) -> List[ToolRegistry]:
        """List all installed tools."""
        return list(self.installed_tools.values())
    
    async def uninstall_tool(self, tool_name: str) -> bool:
        """Uninstall a tool."""
        try:
            if tool_name not in self.installed_tools:
                return False
            
            tool_registry = self.installed_tools[tool_name]
            tool_path = Path(tool_registry.install_path)
            
            # Remove tool files
            import shutil
            if tool_path.exists():
                shutil.rmtree(tool_path)
            
            # Remove from registry
            del self.installed_tools[tool_name]
            
            logger.info(f"Uninstalled tool: {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to uninstall tool {tool_name}: {e}")
            return False

class MCPManager:
    """Main MCP management service."""

    def __init__(self, registry_url: str = "https://smithery.ai/api/v1", tools_dir: Path = Path("./mcp_tools")):
        self.registry = SmitheryRegistry(registry_url)
        self.workbench = McpWorkbench(tools_dir)
        self.auto_install_enabled = True
        self.popular_tools = [
            "web-search", "file-operations", "calculator",
            "weather", "email", "calendar"
        ]

    async def initialize(self):
        """Initialize the MCP manager."""
        logger.info("Initializing MCP Manager")

        # Auto-install popular tools if enabled
        if self.auto_install_enabled:
            await self._auto_install_popular_tools()

    async def _auto_install_popular_tools(self):
        """Auto-install popular tools."""
        logger.info("Auto-installing popular tools")

        for tool_name in self.popular_tools:
            try:
                # Check if already installed
                if tool_name in self.workbench.installed_tools:
                    continue

                # Install tool
                request = ToolInstallRequest(
                    tool_name=tool_name,
                    run_safety_scan=True,
                    requested_by="system"
                )

                response = await self.workbench.install_tool(request, self.registry)

                if response.success:
                    logger.info(f"Auto-installed tool: {tool_name}")
                else:
                    logger.warning(f"Failed to auto-install {tool_name}: {response.message}")

            except Exception as e:
                logger.error(f"Error auto-installing {tool_name}: {e}")

    async def search_tools(self, query: str, **kwargs) -> ToolSearchResponse:
        """Search for tools in the registry."""
        request = ToolSearchRequest(query=query, **kwargs)
        return await self.registry.search_tools(request)

    async def install_tool(self, tool_name: str, version: str = "latest", **kwargs) -> ToolInstallResponse:
        """Install a tool."""
        request = ToolInstallRequest(tool_name=tool_name, version=version, **kwargs)
        return await self.workbench.install_tool(request, self.registry)

    async def execute_tool(self, tool_name: str, function_name: str, parameters: Dict[str, Any], **kwargs) -> ToolExecutionResponse:
        """Execute a tool function."""
        request = ToolExecutionRequest(
            tool_name=tool_name,
            function_name=function_name,
            parameters=parameters,
            **kwargs
        )
        return await self.workbench.execute_tool(request)

    def get_installed_tools(self) -> List[ToolRegistry]:
        """Get list of installed tools."""
        return self.workbench.list_installed_tools()

    async def uninstall_tool(self, tool_name: str) -> bool:
        """Uninstall a tool."""
        return await self.workbench.uninstall_tool(tool_name)

    async def get_tool_info(self, tool_name: str, version: str = "latest") -> Optional[ToolDefinition]:
        """Get information about a tool."""
        return await self.registry.get_tool_info(tool_name, version)

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the MCP system."""
        try:
            # Test registry connection
            search_result = await self.registry.search_tools(ToolSearchRequest(query="test", limit=1))
            registry_healthy = True
        except Exception:
            registry_healthy = False

        installed_tools = self.get_installed_tools()

        return {
            "registry_connection": registry_healthy,
            "installed_tools_count": len(installed_tools),
            "tools_available": sum(1 for tool in installed_tools if tool.status == ToolStatus.INSTALLED),
            "tools_error": sum(1 for tool in installed_tools if tool.status == ToolStatus.ERROR),
            "workbench_healthy": True,  # Could add more checks
            "auto_install_enabled": self.auto_install_enabled
        }

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        installed_tools = self.get_installed_tools()

        total_usage = sum(tool.usage_count for tool in installed_tools)
        total_successes = sum(tool.success_count for tool in installed_tools)
        total_failures = sum(tool.failure_count for tool in installed_tools)

        success_rate = total_successes / max(1, total_successes + total_failures)
        avg_execution_time = sum(tool.avg_execution_time_ms for tool in installed_tools) / max(1, len(installed_tools))

        return {
            "total_tools": len(installed_tools),
            "total_usage": total_usage,
            "success_rate": success_rate,
            "avg_execution_time_ms": avg_execution_time,
            "tools_by_category": self._get_tools_by_category(installed_tools),
            "most_used_tools": self._get_most_used_tools(installed_tools, limit=5)
        }

    def _get_tools_by_category(self, tools: List[ToolRegistry]) -> Dict[str, int]:
        """Group tools by category."""
        categories = {}
        for tool in tools:
            # This would require storing category in ToolRegistry
            # For now, just return a placeholder
            categories["general"] = len(tools)
        return categories

    def _get_most_used_tools(self, tools: List[ToolRegistry], limit: int = 5) -> List[Dict[str, Any]]:
        """Get most used tools."""
        sorted_tools = sorted(tools, key=lambda t: t.usage_count, reverse=True)
        return [
            {
                "name": tool.tool_name,
                "usage_count": tool.usage_count,
                "success_rate": tool.success_count / max(1, tool.usage_count),
                "avg_execution_time_ms": tool.avg_execution_time_ms
            }
            for tool in sorted_tools[:limit]
        ]
