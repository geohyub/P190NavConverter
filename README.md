# P190_NavConverter

> P1/90 항법 포맷 변환 데스크톱 애플리케이션

## Overview

해양 측량에서 표준으로 사용되는 P1/90(UKOOA) 항법 파일을 다양한 포맷으로 변환하는 PySide6 데스크톱 앱입니다.
엔진 레이어(`p190converter/`)와 UI를 분리하여 CLI 및 데스크톱 양쪽에서 사용 가능합니다.

## Key Features

- P1/90 → UTM / 도분초 / GeoJSON / KML / CSV 등 다중 출력 포맷
- 25개 H-record 파싱 (선박 ID, 측선, 측점, CRS 메타)
- 변환 진행률 실시간 표시
- 변환 결과 미리보기 및 검증
- 한국어 / 영어 bilingual UI

## Tech Stack

- **Desktop UI**: PySide6
- **Engine**: `p190converter/` (engine/, models/, utils/)
- **Geometry**: pyproj

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python desktop/main.py
```

## License

Proprietary — Junhyub Kim, GeoView Data QC Team
