"""CLI 명령 핸들러: 입출력编排만 담당, 도메인 로직은 services/providers에 위임 (SRP)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Any

from .. import geo as geo_module
from .. import store as store_module
from ..grading import alert_matches, grade_value_for_metric
from ..parsing import parse_shared_location
from ..providers import factory as providers_factory
from ..providers import openmeteo as openmeteo_module
from ..services import alerts as alerts_service
from ..services import brief as brief_service
from ..services import cron as cron_service
from ..services import regions as regions_service
from ..services import summary as summary_service


def cmd_now(args: argparse.Namespace) -> int:
    region, source = regions_service.resolve_region(args)
    air = providers_factory.fetch_air_quality(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"), provider=args.provider, region=region)
    summary = summary_service.build_summary(region, air, source)
    print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json else summary_service.render_text(summary))
    return 0


def cmd_morning_brief(args: argparse.Namespace) -> int:
    region, source = regions_service.resolve_region(args)
    air = providers_factory.fetch_air_quality(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"), provider=args.provider, region=region)
    summary = summary_service.build_summary(region, air, source)
    weather = openmeteo_module.fetch_weather(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"))
    brief = brief_service.build_morning_brief(summary, weather)
    if args.json:
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    else:
        print(f"{brief['region']} 아침 브리핑")
        print(f"- 날씨: {brief['weather']['summary']} / {brief['weather']['today_min']}~{brief['weather']['today_max']}°C")
        print(f"- 강수 확률: {brief['weather']['precipitation_probability_max']}%")
        print(f"- 초미세먼지: {summary['pm2_5']['value']} μg/m³ · {summary['pm2_5']['grade']}")
        print(f"- 미세먼지: {summary['pm10']['value']} μg/m³ · {summary['pm10']['grade']}")
        print(f"- 종합 판단: {summary['overall_grade']}")
        print(f"- 한줄 요약: {brief['brief']}")
    return 0


def cmd_alert_add(args: argparse.Namespace) -> int:
    rules_payload = store_module.load_alert_rules()
    rules = rules_payload.setdefault("rules", [])
    rule = {"id": len(rules) + 1, "user": args.user, "region": args.region, "metric": args.metric, "threshold": args.threshold, "created_at": datetime.now().isoformat(timespec="seconds")}
    rules.append(rule)
    store_module.save_alert_rules(rules_payload)
    print(json.dumps(rule, ensure_ascii=False, indent=2) if args.json else f"알림 규칙 저장 완료: {args.user} / {args.region} / {args.metric} / {args.threshold} 이상")
    return 0


def cmd_alert_list(args: argparse.Namespace) -> int:
    rules = store_module.load_alert_rules().get("rules", [])
    if args.user:
        rules = [rule for rule in rules if rule.get("user") == args.user]
    if args.json:
        print(json.dumps(rules, ensure_ascii=False, indent=2))
        return 0
    if not rules:
        print("등록된 알림 규칙이 없습니다.")
        return 0
    for rule in rules:
        print(f"- #{rule['id']} {rule['user']} / {rule['region']} / {rule['metric']} / {rule['threshold']} 이상")
    return 0


def cmd_alert_check(args: argparse.Namespace) -> int:
    rules = store_module.load_alert_rules().get("rules", [])
    state = store_module.load_alert_state()
    last_hits = state.setdefault("lastHits", {})
    if args.user:
        rules = [rule for rule in rules if rule.get("user") == args.user]
    hits = []
    for rule in rules:
        region = geo_module.geocode_region(rule["region"])
        air = providers_factory.fetch_air_quality(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"), provider=args.provider, region=region)
        summary = summary_service.build_summary(region, air, "alert-check")
        if not alert_matches(summary, rule["metric"], rule["threshold"]):
            continue
        signature = alerts_service.build_hit_signature(rule, summary)
        last_signature = last_hits.get(str(rule["id"]))
        if not args.emit_all and signature == last_signature:
            continue
        last_hits[str(rule["id"])] = signature
        hits.append({"rule": rule, "summary": summary, "current_grade": grade_value_for_metric(summary, rule["metric"]), "signature": signature})
    store_module.save_alert_state(state)
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return 0
    if getattr(args, "announce_text", False):
        if not hits:
            print("NO_REPLY")
            return 0
        metric_labels = {"pm2_5": "초미세먼지", "pm10": "미세먼지", "ozone": "오존", "khai": "통합대기(KHAI)", "overall": "종합 대기질"}
        lines = []
        for hit in hits:
            summary = hit["summary"]
            rule = hit["rule"]
            m_name = metric_labels.get(rule["metric"], rule["metric"])
            measured_at = summary.get("measured_at") or "측정 시각 없음"
            station_info = f" ({summary['station_name']} 측정소)" if summary.get("station_name") else ""
            lines.append(
                f"{rule['region']}{station_info} {m_name} 알림: 현재 등급 {hit['current_grade']}(기준: {rule['threshold']} 이상), "
                f"초미세먼지 {summary['pm2_5']['value']}㎍/㎥ / 미세먼지 {summary['pm10']['value']}㎍/㎥, 측정 시각 {measured_at}."
            )
        print("\n".join(lines))
        return 0
    if not hits:
        print("현재 조건을 만족하는 신규 알림 항목이 없습니다.")
        return 0
    for hit in hits:
        print(f"- {hit['rule']['region']} / {hit['rule']['metric']} / 현재 {hit['current_grade']} / 기준 {hit['rule']['threshold']} 이상")
        print(f"  초미세먼지 {hit['summary']['pm2_5']['value']}({hit['summary']['pm2_5']['grade']}), 미세먼지 {hit['summary']['pm10']['value']}({hit['summary']['pm10']['grade']})")
    return 0


def cmd_alert_remove(args: argparse.Namespace) -> int:
    rules_payload = store_module.load_alert_rules()
    rules = rules_payload.get("rules", [])
    before_count = len(rules)

    if getattr(args, "all", False):
        if args.user:
            rules_payload["rules"] = [r for r in rules if r.get("user") != args.user]
        else:
            rules_payload["rules"] = []
    elif getattr(args, "id", None) is not None:
        target_id = int(args.id)
        if args.user:
            rules_payload["rules"] = [r for r in rules if not (r.get("id") == target_id and r.get("user") == args.user)]
        else:
            rules_payload["rules"] = [r for r in rules if r.get("id") != target_id]
    else:
        raise ValueError("--id <rule_id> 또는 --all 옵션을 지정하세요.")

    removed_count = before_count - len(rules_payload["rules"])
    store_module.save_alert_rules(rules_payload)
    msg = f"알림 규칙 삭제 완료 ({removed_count}건 삭제됨)"
    print(json.dumps({"removed_count": removed_count, "remaining_count": len(rules_payload["rules"])}, ensure_ascii=False, indent=2) if args.json else msg)
    return 0


def cmd_cron_plan(args: argparse.Namespace) -> int:
    plan = cron_service.build_cron_plan(args.kind, args.user, args.region, args.metric, args.threshold, args.hour, args.minute)
    print(json.dumps(plan, ensure_ascii=False, indent=2) if args.json else f"권장 cron expr: {plan['schedule']['expr']}\njob name: {plan['name']}")
    return 0


def cmd_save_default(args: argparse.Namespace) -> int:
    prefs = store_module.load_preferences()
    users = prefs.setdefault("users", {})
    info = users.setdefault(args.user, {})
    info["default_region"] = args.region
    store_module.save_preferences(prefs)
    print(f"기본 지역 저장 완료: {args.user} -> {args.region}")
    return 0


def cmd_clear_default(args: argparse.Namespace) -> int:
    prefs = store_module.load_preferences()
    users = prefs.get("users", {})
    if args.user in users:
        users.pop(args.user, None)
        store_module.save_preferences(prefs)
        msg = f"기본 지역 및 위치 삭제 완료: {args.user}"
    else:
        msg = f"저장된 기본 지역/위치 설정이 없습니다: {args.user}"
    print(json.dumps({"user": args.user, "cleared": True}, ensure_ascii=False, indent=2) if args.json else msg)
    return 0


def cmd_save_location(args: argparse.Namespace) -> int:
    shared = parse_shared_location(getattr(args, "location_text", None))
    lat = args.lat
    lon = args.lon
    label = args.label
    if shared:
        lat = shared["lat"]
        lon = shared["lon"]
        label = label or shared.get("label")
    if lat is None or lon is None:
        raise ValueError("위치 좌표를 확인할 수 없습니다. lat/lon 또는 --location-text 를 넣어 주세요.")
    prefs = store_module.load_preferences()
    users = prefs.setdefault("users", {})
    info = users.setdefault(args.user, {})
    info["default_location"] = {"lat": lat, "lon": lon, "label": label}
    store_module.save_preferences(prefs)
    print(f"기본 위치 저장 완료: {args.user} -> ({lat}, {lon})" + (f" / {label}" if label else ""))
    return 0


def cmd_show_default(args: argparse.Namespace) -> int:
    prefs = store_module.load_preferences()
    info = prefs.get("users", {}).get(args.user, {})
    payload = {"user": args.user, "default_region": info.get("default_region"), "default_location": info.get("default_location")}
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else (json.dumps(payload, ensure_ascii=False) if info else "저장된 기본 설정이 없습니다."))
    return 0


def cmd_setup_provider(args: argparse.Namespace) -> int:
    cfg = store_module.load_config()
    cfg["provider"] = args.provider
    if args.airkorea_api_key is not None:
        cfg["airkorea_api_key"] = args.airkorea_api_key
    store_module.save_config(cfg)
    print(json.dumps(cfg, ensure_ascii=False, indent=2) if args.json else f"기본 provider 저장 완료: {args.provider}")
    return 0


def cmd_show_config(args: argparse.Namespace) -> int:
    cfg = store_module.load_config()
    redacted = dict(cfg)
    if redacted.get("airkorea_api_key"):
        redacted["airkorea_api_key"] = "***configured***"
    print(json.dumps(redacted, ensure_ascii=False, indent=2) if args.json else f"provider={redacted.get('provider')} airkorea_api_key={redacted.get('airkorea_api_key')}")
    return 0


def cmd_resolve_region(args: argparse.Namespace) -> int:
    region = geo_module.geocode_region(args.region)
    print(json.dumps(region, ensure_ascii=False, indent=2) if args.json else f"{args.region} -> {region['resolved_name']} ({region['latitude']}, {region['longitude']})")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    results = []
    errors = []
    for region_name in args.regions:
        try:
            region = geo_module.geocode_region(region_name)
            air = providers_factory.fetch_air_quality(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"), provider=args.provider, region=region)
            results.append(summary_service.build_summary(region, air, "query"))
        except Exception as exc:
            errors.append({"region": region_name, "error": str(exc)})
    if args.json:
        payload: Any = results if not errors else {"results": results, "errors": errors}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    for item in results:
        print(f"- {item['resolved_region']}: PM2.5 {item['pm2_5']['value']}({item['pm2_5']['grade']}), PM10 {item['pm10']['value']}({item['pm10']['grade']}), 종합 {item['overall_grade']}")
    for err in errors:
        print(f"- [조회 실패] {err['region']}: {err['error']}")
    return 0
