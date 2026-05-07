from .mixin_lifecycle import LifecycleMixin
from .mixin_config import ConfigMixin
from .mixin_detection import DetectionMixin
from .mixin_actions import ActionsMixin
from .mixin_webhook import WebhookMixin
from .mixin_remote import RemoteMixin
from .mixin_recorder import RecorderMixin

class LegacyBiomeTracker(
    LifecycleMixin,
    ConfigMixin,
    DetectionMixin,
    ActionsMixin,
    WebhookMixin,
    RemoteMixin,
    RecorderMixin,
):
    pass
