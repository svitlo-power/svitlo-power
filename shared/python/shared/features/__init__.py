"""Feature flag infrastructure."""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import os


class FeatureFlag(str, Enum):
    """Feature flags for migration phases."""
    # Phase 1: Dashboard snapshot publishing
    DASHBOARD_SNAPSHOT_PUBLISH = "dashboard_snapshot_publish"
    
    # Phase 2: App back-end Redis reads
    APP_BACKEND_REDIS_READS = "app_backend_redis_reads"
    
    # Phase 3: SSE migration
    BACKEND_SSE_REDIS = "backend_sse_redis"
    APP_BACKEND_SSE_REDIS = "app_backend_sse_redis"
    
    # Phase 4-5: Processing service
    PROCESSING_SHADOW_MODE = "processing_shadow_mode"
    PROCESSING_CUTOVER = "processing_cutover"
    
    # Phase 6: Capability migration
    MESSAGE_PREVIEW_PROCESSING = "message_preview_processing"
    ADMIN_CRUD_PROCESSING = "admin_crud_processing"
    DEYE_POLLING_PROCESSING = "deye_polling_processing"
    CLEANUP_PROCESSING = "cleanup_processing"
    MESSAGE_DELIVERY_PROCESSING = "message_delivery_processing"
    
    # Phase 7: Identity
    IDENTITY_SERVICE = "identity_service"
    
    # Phase 8: App separation
    PUBLIC_ADMIN_SEPARATION = "public_admin_separation"


@dataclass
class FeatureFlagConfig:
    """Configuration for a feature flag."""
    flag: FeatureFlag
    enabled: bool = False
    description: str = ""
    rollout_percentage: int = 100  # 0-100
    environments: list[str] = field(default_factory=lambda: ["production", "staging", "development"])


class FeatureFlags:
    """Feature flag manager."""
    
    def __init__(self):
        self._flags: dict[FeatureFlag, FeatureFlagConfig] = {}
        self._load_from_env()
    
    def _load_from_env(self):
        """Load feature flags from environment variables."""
        for flag in FeatureFlag:
            env_var = f"FEATURE_{flag.value.upper()}"
            enabled = os.getenv(env_var, "false").lower() == "true"
            
            rollout_env = f"FEATURE_{flag.value.upper()}_ROLLOUT"
            rollout = int(os.getenv(rollout_env, "100"))
            
            self._flags[flag] = FeatureFlagConfig(
                flag=flag,
                enabled=enabled,
                rollout_percentage=rollout,
            )
    
    def is_enabled(self, flag: FeatureFlag, context: Optional[dict] = None) -> bool:
        """Check if a feature flag is enabled."""
        config = self._flags.get(flag)
        if not config:
            return False
        
        if not config.enabled:
            return False
        
        # Check rollout percentage
        if config.rollout_percentage < 100:
            # Simple deterministic rollout based on context
            if context and "user_id" in context:
                user_hash = hash(str(context["user_id"])) % 100
                return user_hash < config.rollout_percentage
            elif context and "request_id" in context:
                req_hash = hash(str(context["request_id"])) % 100
                return req_hash < config.rollout_percentage
            else:
                # Default to enabled for non-user contexts (e.g., scheduled jobs)
                return True
        
        return True
    
    def get_config(self, flag: FeatureFlag) -> Optional[FeatureFlagConfig]:
        """Get feature flag configuration."""
        return self._flags.get(flag)
    
    def set_enabled(self, flag: FeatureFlag, enabled: bool):
        """Set feature flag enabled state (runtime override)."""
        if flag in self._flags:
            self._flags[flag].enabled = enabled
        else:
            self._flags[flag] = FeatureFlagConfig(flag=flag, enabled=enabled)
    
    def get_all_flags(self) -> dict[str, bool]:
        """Get all flags as a dict of flag_name -> enabled."""
        return {flag.value: config.enabled for flag, config in self._flags.items()}


# Global instance
feature_flags = FeatureFlags()