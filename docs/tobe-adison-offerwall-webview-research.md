---
type: analysis
title: 투비 애디슨 오퍼월 WebView 적용성
canonical_id: analysis:tobe/adison-offerwall-webview
status: draft
updated_at: 2026-09-01
service_id: tobe
related_services:
  - "[[tobe]]"
related_domains: []
related_tickets: []
related_okrs: []
relation_status: inferred
relation_sources:
  - manual
---

# 투비 애디슨 오퍼월 WebView 적용성

## 결론

| 대상 | 판정 | 조건 |
| --- | --- | --- |
| 네이티브 Android/iOS 앱 | 지원 | 애디슨 네이티브 SDK와 캠페인 완료 API를 각각 연동 |
| 네이티브 셸 안의 WebView 앱 | 적용 가능 | 네이티브 셸에 애디슨 SDK를 넣고 WebView–네이티브 브리지를 구현 |
| 순수 모바일 웹/PWA | 공개 문서상 지원 경로 없음 | 브라우저만으로는 애디슨 네이티브 SDK 브리지와 앱 식별자가 없어 운영 연동 불가 |

현재 애디슨 오퍼월 공개 v5 문서는 클라이언트 연동을 Android SDK/iOS SDK로, 보상 처리를 서버 연동인 Campaign API로 설명한다. 웹 브라우저 전용 SDK는 현재 공개 가이드에 열거되어 있지 않다 ([공식 가이드](https://docs.adison.co/offerwall), [가이드 목차](https://docs.adison.co/offerwall/llms.txt)). 따라서 “앱에서만”이라는 표현은 순수 웹이 아니라 **앱 클라이언트가 필요하다**는 의미로 이해하는 것이 안전하다.

다만 WebView 하이브리드 앱은 별도 판단이다. 애디슨 운영사 NBT가 WebView로 구현된 매체 지원을 위해 “애디슨 웹뷰 SDK”를 개발했다고 명시했고 ([NBT 공식 글](https://nbtway.oopy.io/8d5832cd-e815-48e1-acfd-0f156501c194)), 공식 GitHub에는 WebView SDK 샘플과 `adison-offerwall-webview-sdk` 사용 샘플이 있다 ([WebView 샘플](https://github.com/adison-ads/adison-ofw-webview-samples/blob/main/11st/index.html), [BankSalad 샘플](https://github.com/adison-ads/adison-ofw-webview-sample-banksalad/blob/main/pages/sample.tsx), [NPM 패키지](https://www.npmjs.com/package/adison-offerwall-webview-sdk)). 즉 투비처럼 네이티브 셸이 있는 앱은 적용 대상이 될 수 있지만, 웹 프론트만 배포해서는 안 된다.

## 권장 연동 구조

```text
투비 WebView의 오퍼월 버튼
        │ 기존 aladinBridge
        ▼
Android/iOS 네이티브 셸 → 애디슨 네이티브 SDK의 오퍼월 표시
        ▼
오퍼월/캠페인 랜딩
        ▼
애디슨 캠페인 완료 콜백 → 투비 보상 API(HMAC 검증)
```

- 네이티브 계층: 현재 SDK 최소 OS는 Android API 23(Android 6.0), iOS 13.0이다 ([Android 시작하기](https://docs.adison.co/offerwall/android-quick-start.md), [iOS 시작하기](https://docs.adison.co/offerwall/ios-quick-start.md)). Android/iOS 및 DEV/PRD별 매체 키가 분리되므로 올바른 키를 사용해야 한다 ([매체 연동 프로세스 안내](https://docs.google.com/presentation/d/1AFvDVgw6yzcnGMDbfpvzsk9CP6nwjzAs-sn606BZgfk/edit?usp=sharing)).
- WebView 계층: 전체 오퍼월을 여는 용도라면 기존 투비 `aladinBridge`에 명령 하나를 추가해 네이티브 SDK의 표시 함수를 호출하는 방식이 가장 단순하다. 웹 페이지 안에 개별 광고 목록을 직접 조회·렌더링하려는 경우에는 별도로 공개된 WebView 패키지가 `Ofw.init({ mode, android, ios })`, `loadAds()`, `showOfferwall()`과 Android/iOS의 `AdisonOfwBridge` 연결 방식을 제공한다 ([샘플 소스](https://github.com/adison-ads/adison-ofw-webview-samples/blob/main/11st/index.html), [패키지](https://www.npmjs.com/package/adison-offerwall-webview-sdk)). 이 패키지의 NPM 최신 공개 버전은 `0.9.12`(2024-08-12 배포)이고 현재 v5 공식 연동 문서에는 포함되지 않으므로, 인라인 광고형을 선택할 때는 v5 호환성과 최신 브리지 구현을 애디슨에 확인해야 한다.
- 사용자 식별: SDK UID는 안정적인 투비 회원 식별자로 설정하고, 최대 80자 및 로그아웃/회원 삭제 시 해제 규칙을 따른다 ([Android 로그인](https://docs.adison.co/offerwall/android-quick-start/login.md)). UID는 보상 API의 `uid`와 동일한 값이어야 한다.
- 보상 처리: 캠페인 완료는 애디슨이 투비 서버의 완료 API를 호출하는 서버-투-서버 흐름이다. 투비 서버는 HMAC을 검증한 뒤 중복 방지와 원장 기록 후 보상을 지급해야 한다 ([Campaign 완료 API](https://docs.adison.co/offerwall/campaigns-api/complete.md), [Campaign API 개요](https://docs.adison.co/offerwall/campaigns-api.md)).

## 투비 코드와의 접점

공개된 투비 앱 저장소는 이미 “네이티브 셸 + WebView + JavaScript 브리지” 구조다. Android는 `MainFragment`에서 WebView에 `aladinBridge`를 주입하고 ([Android MainFragment](https://github.com/AladinCommunication/ToBeAndroid/blob/main/app/src/main/java/kr/co/aladin/tobe/MainFragment.kt)), iOS는 `WKScriptMessageHandler`로 같은 역할을 한다 ([iOS message handler](https://github.com/AladinCommunication/ToBeIos/blob/main/AladinToBeContinued/ViewController/MainWebView/MainWebViewController%2BWKScriptMessageHandler.swift)). 현재 브리지는 AdMob용이므로 이를 그대로 재사용한다는 뜻은 아니며, 각 OS 네이티브 계층에 애디슨 SDK 초기화·키·새 브리지 명령을 추가한다. 개별 광고를 웹 페이지에 직접 렌더링하는 안을 선택할 때만 WebView 웹 코드에 애디슨 WebView 패키지와 전용 `AdisonOfwBridge`를 추가한다.

## 제한 사항과 확인할 점

- 순수 웹에서 `showOfferwall()`을 호출하는 것만으로는 충분하지 않다. 공식 WebView 패키지는 네이티브 브리지를 전제로 하므로, 브리지가 없는 Safari/Chrome/PWA를 운영 경로로 잡지 않는다. WebView SDK의 현재 패키지 버전·지원 OS·브리지 명세는 공개 v5 문서와 분리되어 있으므로 애디슨에 최신 배포본과 연동 승인을 확인한다.
- 공식 자료에서 커스텀 User-Agent를 필수로 요구한다는 내용은 확인되지 않았다. 별도 UA는 애디슨이 요구할 때만 추가한다. 앱스토어 심사 면제/보장도 공식 자료에서 확인되지 않았으므로 일반 Android/iOS 광고·딥링크 정책과 투비 앱 심사를 별도로 검토한다.
- 광고주 랜딩이 외부 브라우저·설치 앱·intent/deep link를 사용할 수 있으므로 Android WebView와 `WKWebView`의 외부 URL/팝업/뒤로가기 처리를 실제 캠페인으로 검증한다. 이 항목은 애디슨 문서의 필수 설정이라기보다 하이브리드 앱 구현 검증 항목이다.
- 매체 연동 프로세스상 패키지명, 마켓 링크, 최소 지원 OS, DEV/PRD 앱 키와 QA 절차를 애디슨에 제출해야 한다 ([연동 프로세스 안내](https://docs.google.com/presentation/d/1AFvDVgw6yzcnGMDbfpvzsk9CP6nwjzAs-sn606BZgfk/edit?usp=sharing)).

## 권고

투비는 Android/iOS 네이티브 셸을 유지하는 **하이브리드 연동**으로 진행할 수 있다. 구현 착수 전 애디슨에 `adison-offerwall-webview-sdk`의 현재 권장 버전, `AdisonOfwBridge` 명세, 투비용 Android/iOS DEV·PRD 키, 외부 랜딩 정책을 확인하고, 이후 UID 일치·완료 콜백/HMAC·중복 보상·로그아웃·딥링크를 양 OS에서 검증한다. 순수 모바일 웹/PWA만으로 같은 기능을 제공하는 안은 현재 공식 공개 지원 범위 밖이다.

## 관련

- 서비스 카탈로그: [`catalog/tobe.yaml`](../catalog/tobe.yaml)
- 공식 Android SDK: https://docs.adison.co/offerwall/android-quick-start.md
- 공식 iOS SDK: https://docs.adison.co/offerwall/ios-quick-start.md
