# Silver Information

RSS 기반으로 패션 기사를 자동 수집 → 브랜드 태그로 필터링 → 개인 매거진 웹페이지 생성.
선택적으로 내 말투로 재작성한 콘텐츠 초안까지 매일 자동 생성.

## 구조
```
config/feeds.txt         # 수집할 RSS 피드 목록
config/brands.txt        # 필터링할 브랜드/키워드 (비어있으면 전체 수집)
config/style_samples.md  # 내 예전 블로그 글 샘플 (말투 재작성용)
scripts/fetch_and_filter.py  # 1단계: 수집 + 필터링 + 이미지/본문 보강
scripts/generate_site.py     # 2단계: 매거진 웹페이지 생성 (docs/index.html)
scripts/style_rewrite.py     # 3단계: 내 어투로 재작성한 초안 생성 (docs/drafts/)
scripts/instagram_card.py    # 4단계: 기사별 인스타그램 카드뉴스 이미지 생성 (docs/instagram/)
scripts/generate_instagram_gallery.py  # 인스타 카드 갤러리 페이지 생성
assets/fonts/                 # 카드 렌더링용 Pretendard 폰트
data/articles.json        # 누적 저장된 기사 데이터
.github/workflows/update.yml  # 매일 자동 실행 (GitHub Actions)
```

## 설정 방법

1. **GitHub 저장소 생성**
   - 이 폴더 전체를 새 GitHub 저장소로 push
   - Settings → Pages → Source를 `main` 브랜치의 `/docs` 폴더로 설정
   - 몇 분 후 `https://<계정명>.github.io/<저장소명>/` 에서 매거진 확인 가능

2. **관심 브랜드 등록**
   - `config/brands.txt`에 원하는 브랜드/키워드 추가 (예: Rick Owens, Margiela, denim)
   - 비워두면 등록된 모든 피드의 기사를 가져옴

3. **RSS 피드 조정**
   - `config/feeds.txt`에서 원하는 매체 추가/삭제
   - 각 매체 사이트에 들어가서 RSS 주소를 확인하고 교체하면 됨

4. **(선택) 내 어투로 초안 자동 생성**
   - `config/style_samples.md`에 예전 블로그 글 2~3편 붙여넣기
   - 저장소 Settings → Secrets and variables → Actions → New repository secret
     - Name: `ANTHROPIC_API_KEY`
     - Value: 본인의 Anthropic API 키 (console.anthropic.com 에서 발급)
   - 키를 등록하지 않으면 이 단계는 자동으로 건너뛰고 나머지는 정상 동작함

5. **실행 주기 변경**
   - `.github/workflows/update.yml`의 cron 값 수정 (`0 22 * * *` = 한국시간 매일 오전 7시)
   - 당장 테스트해보고 싶으면 저장소의 Actions 탭 → "Update Fashion Magazine" → Run workflow로 수동 실행 가능

## 로컬에서 미리 테스트하기
```bash
pip install -r requirements.txt
python scripts/fetch_and_filter.py
python scripts/generate_site.py
# 브랜드 초안까지 테스트하려면:
export ANTHROPIC_API_KEY=sk-...
python scripts/style_rewrite.py
open docs/index.html
```

## 이미지 & 본문 보강
- RSS 안에 썸네일이 있으면 그대로 사용
- 없으면 기사 링크에 접속해서 `og:image`(대표 이미지)와 `og:description`(요약)을 읽어와 보강
- `og:image`도 없는데 유튜브/비메오 영상이 삽입된 페이지(패션쇼 영상 리뷰 기사 등)라면, 그 영상의 대표 프레임(썸네일)을 대신 가져옴
- 한 번 실행에 최대 30건까지만 보강 요청을 보냄 (`fetch_and_filter.py`의 `MAX_ENRICH_FETCHES`로 조정 가능)
- 이미지가 아예 없는 기사는 텍스트만 있는 카드로 표시됨

## 티스토리 복사-붙여넣기
- 어투 재작성 초안이 생성될 때마다 `docs/drafts/<날짜>.html`도 같이 만들어짐
- 매거진 메인 페이지 → "✏️ 초안 목록" → 원하는 날짜 클릭 → "복사하기" 버튼 → 티스토리 새 글 편집기에 붙여넣기(Ctrl+V)
- 문단 구조가 유지된 채로 복사되도록 만들어져 있음

## 인스타그램 카드뉴스
- 필터링된 기사마다 1080x1080 다크 톤 텍스트 카드가 자동 생성됨 (`scripts/instagram_card.py`)
- 폰트는 Pretendard(무료, `assets/fonts/`에 포함), 배경 검정 + 흰 글씨
- 카드 상단: 매칭된 브랜드명 / 중앙: 기사 제목 / 하단: 출처
- `docs/instagram/<날짜>/`에 PNG로 저장, 메인 페이지 → "🖼 인스타 카드"에서 갤러리로 모아보기 가능
- 다운받아서 인스타그램에 그대로 업로드하면 됨

## 나중에 확장하고 싶다면
- 브랜드별 페이지 분리, 검색 기능 추가
- 초안(`docs/drafts/*.md`)을 실제 블로그 플랫폼에 자동 포스팅하는 단계 추가
