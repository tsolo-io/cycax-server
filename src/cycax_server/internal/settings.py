# SPDX-FileCopyrightText: 2025 Tsolo.io
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CYCAX_")

    var_dir: Path = Path("/tmp/cycax_server/var")  # noqa: S108 - No security concern with placing files in temp.
    freecad_enabled: bool = True
    keep_age_hours: int = 50
    debug: bool = False
