from dataclasses import dataclass, field


@dataclass(frozen=True)
class FamilyValidation:
    # Validation markers stay small and string-based because they are used to
    # assert generated source characteristics without importing generated code.
    backend_markers: tuple[str, ...] = field(default_factory=tuple)
    frontend_markers: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, value):
        if not value:
            return cls()
        return cls(
            backend_markers=tuple(value.get("backend_markers", ())),
            frontend_markers=tuple(value.get("frontend_markers", ())),
        )

    def as_mapping(self):
        return {
            "backend_markers": self.backend_markers,
            "frontend_markers": self.frontend_markers,
        }


@dataclass(frozen=True)
class FamilyPack:
    # A family pack is the plugin contract for one supported app family.
    app_type: str
    extension: dict = field(default_factory=dict)
    validation: FamilyValidation = field(default_factory=FamilyValidation)

    @property
    def backend_markers(self):
        return self.validation.backend_markers

    @property
    def frontend_markers(self):
        return self.validation.frontend_markers

    @property
    def has_extension(self):
        return bool(self.extension)


def build_family_pack(app_type, extension=None, validation=None):
    return FamilyPack(
        app_type=app_type,
        extension=extension or {},
        validation=FamilyValidation.from_mapping(validation),
    )
