import asyncpg
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from mcp.server.fastmcp import FastMCP, Context

# Initialize the FastMCP Server for RigEye
mcp = FastMCP("RigEye-OT-Bridge")

# =====================================================================
# 1. PYDANTIC SCHEMAS (Data Contracts & Validation)
# =====================================================================

class TelemetryQuerySchema(BaseModel):
    well_id: str = Field(..., description="Unique well identifier, e.g., 'WELL-NORTHSEA-42A'")
    channel: str = Field(..., description="WITSML channel mnemonic, e.g., 'ROP', 'SPP', 'HKLD', 'BIT_DEPTH'")
    time_window_minutes: int = Field(default=15, ge=1, le=120, description="Lookback window in minutes (1-120)")

class MaintenanceTicketSchema(BaseModel):
    asset_id: str = Field(..., description="Equipment tag, e.g., 'PUMP-TOPDRIVE-01'")
    severity: str = Field(..., description="Urgency: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'")
    anomaly_type: str = Field(..., description="Classified anomaly, e.g., 'Vibration Spike', 'Thermal Exceedance'")
    telemetry_snapshot: Dict[str, Any] = Field(..., description="JSON payload of telemetry triggering the ticket")
    recommended_action: str = Field(..., description="Actionable recommendation for field crew")

    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid_levels = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid severity '{v}'. Must be one of {valid_levels}")
        return v.upper()


# =====================================================================
# 2. MCP RESOURCES (Exposing Real-Time State & Logs)
# =====================================================================

@mcp.resource("rigeye://well/{well_id}/active_alerts")
async def get_well_alerts(well_id: str) -> str:
    """
    Exposes real-time active alarms for a specific offshore asset.
    LLM agents can read this resource to ground reasoning in live status.
    """
    # Mocking database query to WITSML/SCADA telemetry store
    active_alerts = [
        {"timestamp": "2026-10-29T14:15:02Z", "channel": "SPP", "value": 4250.5, "unit": "psi", "status": "HIGH_ALARM"},
        {"timestamp": "2026-10-29T14:18:11Z", "channel": "TOPDRIVE_TEMP", "value": 98.2, "unit": "degC", "status": "WARNING"}
    ]
    return f"Active Alerts for Asset {well_id}:\n" + str(active_alerts)


# =====================================================================
# 3. MCP TOOLS (Deterministic Tool-Calling Execution)
# =====================================================================

@mcp.tool()
async def query_witsml_telemetry(params: TelemetryQuerySchema, ctx: Context) -> Dict[str, Any]:
    """
    Ingest and aggregate high-frequency WITSML time-series data for a specified well and channel.
    Returns calculated statistical metrics (mean, max, trend vector) to conserve LLM token context.
    """
    ctx.info(f"Ingesting time-series for {params.well_id} [{params.channel}] over last {params.time_window_minutes}m")
    
    # Simulate high-frequency streaming aggregation (WITSML -> Pandas/NumPy vector)
    # In production, this queries InfluxDB / TimescaleDB / OSIsoft PI
    aggregated_data = {
        "well_id": params.well_id,
        "channel": params.channel,
        "window_minutes": params.time_window_minutes,
        "sample_count": 900,  # 1Hz sampling
        "metrics": {
            "current_value": 312.4,
            "mean": 305.1,
            "max": 345.8,
            "unit": "m/hr" if params.channel == "ROP" else "psi",
            "trend": "INCREASING_STEEP"
        },
        "anomaly_flag": True if params.channel == "SPP" else False
    }
    
    return {
        "status": "SUCCESS",
        "data": aggregated_data
    }


@mcp.tool()
async def trigger_ifs_maintenance_ticket(ticket: MaintenanceTicketSchema, ctx: Context) -> Dict[str, Any]:
    """
    Dispatches a structured maintenance work order directly into enterprise ERP/CMMS (IFS / SAP).
    Includes Pydantic validation and returns a tracking confirmation ID.
    """
    ctx.info(f"Dispatching IFS Work Order for asset {ticket.asset_id} [Severity: {ticket.severity}]")
    
    # Simulate API execution against IFS REST API
    ticket_id = f"IFS-WO-2026-{abs(hash(ticket.asset_id)) % 10000:04d}"
    
    return {
        "status": "CREATED",
        "ticket_id": ticket_id,
        "asset_id": ticket.asset_id,
        "severity": ticket.severity,
        "dispatch_status": "QUEUED_FOR_FIELD_ENGINEER",
        "audit_trail": {
            "created_by_agent": "RigEye-Autonomous-Monitor",
            "timestamp": "2026-10-29T14:24:00Z"
        }
    }


# =====================================================================
# 4. SERVER ENTRYPOINT
# =====================================================================

if __name__ == "__main__":
    # Runs the MCP server over stdio (JSON-RPC 2.0 transport)
    mcp.run(transport="stdio")
