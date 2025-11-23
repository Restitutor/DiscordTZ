import contextlib
from pathlib import Path
from typing import Final, List, Dict

import tzlocal


class Timezones:
    LOCAL_TZ: Final[str] = tzlocal.get_localzone().key

    @staticmethod
    def _fetchTimezones() -> List[Dict[str, str]]:
        files: list[dict[str, str]] = []
        for root, _dirs, filenames in Path("/usr/share/zoneinfo/").walk():
            if root.name == "posix":
                continue
            for filename in filenames:
                filePath = root / filename
                with contextlib.suppress(ValueError):
                    relativePath = filePath.relative_to(Path("/usr/share/zoneinfo/"))

                if len(relativePath.parts) > 1:
                    files.append({"area": relativePath.parts[0], "city": relativePath.parts[-1].replace("_", " ")})

        return files

    TIMEZONES: Final[List[Dict[str, str]]] = _fetchTimezones()
    CHECK_LIST: List[str] = [tz["area"] + "/" + tz["city"] for tz in TIMEZONES]
