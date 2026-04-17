#!/usr/bin/env bash
# verify_phase5.sh — Verify Phase 5 (Demo & Polish) is complete
# Run from the repository root: bash scripts/verify_phase5.sh

PASS=0
FAIL=0
WARN=0

check() {
    local label="$1"
    local result="$2"
    local detail="${3:-}"
    if [ "$result" = "pass" ]; then
        printf "  ✓ %s\n" "$label"
        PASS=$((PASS + 1))
    elif [ "$result" = "warn" ]; then
        printf "  ⚠ %s" "$label"
        [ -n "$detail" ] && printf " — %s" "$detail"
        printf "\n"
        WARN=$((WARN + 1))
    else
        printf "  ✗ %s" "$label"
        [ -n "$detail" ] && printf " — %s" "$detail"
        printf "\n"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "SecuriSphere Phase 5 Verification"
echo "═══════════════════════════════════════"
echo ""

echo "[ Files ]"
[ -f "scripts/run_demo.sh" ]                          && check "scripts/run_demo.sh exists"           pass || check "scripts/run_demo.sh exists"           fail "not found"
[ -f "scripts/verify_phase5.sh" ]                     && check "scripts/verify_phase5.sh exists"      pass || check "scripts/verify_phase5.sh exists"      warn "this file"
[ -f "frontend/src/components/DemoBanner.jsx" ]        && check "DemoBanner.jsx exists"               pass || check "DemoBanner.jsx exists"                fail "not found"
[ -f "evaluation/baseline_mttd.py" ]                   && check "baseline_mttd.py exists"             pass || check "baseline_mttd.py exists"             fail "not found"
[ -f "engine/narration/narrator.py" ]                  && check "narrator.py exists"                  pass || check "narrator.py exists"                  fail "not found"
[ -f "tests/test_narrator.py" ]                        && check "tests/test_narrator.py exists"       pass || check "tests/test_narrator.py exists"       fail "not found"
[ -f "tests/test_smoke.py" ]                           && check "tests/test_smoke.py exists"          pass || check "tests/test_smoke.py exists"          fail "not found"

echo ""
echo "[ scripts/run_demo.sh content ]"
grep -q "All services healthy"  scripts/run_demo.sh   && check "health polling present"              pass || check "health polling present"              fail "old interactive menu still in place"
grep -q "xdg-open\|open http"   scripts/run_demo.sh   && check "browser open present"               pass || check "browser open present"               fail "missing browser open logic"
grep -q "demo:active"           scripts/run_demo.sh   && check "Redis demo flag set"                pass || check "Redis demo flag set"                fail "missing Redis demo flag"
grep -q "Launching attack"      scripts/run_demo.sh   && check "countdown present"                  pass || check "countdown present"                  fail "missing countdown"

echo ""
echo "[ Makefile targets ]"
grep -q "^attack-fast:"    Makefile  && check "attack-fast target"      pass || check "attack-fast target"      fail "missing"
grep -q "^attack-demo:"    Makefile  && check "attack-demo target"      pass || check "attack-demo target"      fail "missing"
grep -q "^attack-slow:"    Makefile  && check "attack-slow target"      pass || check "attack-slow target"      fail "missing"
grep -q "^reset:"          Makefile  && check "reset target"            pass || check "reset target"            fail "missing"
grep -q "^evaluate-full:"  Makefile  && check "evaluate-full target"    pass || check "evaluate-full target"    warn "optional"
grep -q "^ci:"             Makefile  && check "ci target"               pass || check "ci target"               fail "missing"
grep -q "^demo-full:"      Makefile  && check "demo-full target"        pass || check "demo-full target"        fail "missing"
grep -q "^health-full:"    Makefile  && check "health-full target"      pass || check "health-full target"      fail "missing"
grep -q "^verify-phase5:"  Makefile  && check "verify-phase5 target"   pass || check "verify-phase5 target"   fail "missing"
grep -q "^mttd-markdown:"  Makefile  && check "mttd-markdown target"   pass || check "mttd-markdown target"   fail "missing"
grep -q "^test-narrator:"  Makefile  && check "test-narrator target"   pass || check "test-narrator target"   fail "missing"
grep -q "^test-smoke:"     Makefile  && check "test-smoke target"      pass || check "test-smoke target"      fail "missing"

echo ""
echo "[ simulation/run_all.py ]"
grep -q "speed"   simulation/run_all.py && check "--speed argument added"  pass || check "--speed argument added"  fail "not found"
grep -q "SPEED_MAP\|speed_map" simulation/run_all.py && check "SPEED_MAP dict present" pass || check "SPEED_MAP dict present" warn "may use different variable name"

echo ""
echo "[ Backend endpoints — requires stack running ]"
if curl -sf http://localhost:8000/api/demo-status > /dev/null 2>&1; then
    check "/api/demo-status reachable"  pass
else
    check "/api/demo-status reachable"  warn "stack not running — start with 'make start' to verify"
fi
if curl -sf http://localhost:8000/api/mttd/report > /dev/null 2>&1; then
    check "/api/mttd/report reachable"  pass
else
    check "/api/mttd/report reachable"  warn "stack not running — start with 'make start' to verify"
fi

echo ""
echo "═══════════════════════════════════════"
printf "  Results: %d passed, %d warnings, %d failed\n" "$PASS" "$WARN" "$FAIL"
echo "═══════════════════════════════════════"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "  Some checks failed. Fix the items marked ✗ above."
    exit 1
else
    echo "  Phase 5 verification complete ✓"
    exit 0
fi
