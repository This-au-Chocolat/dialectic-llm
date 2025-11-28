"""Test script para verificar configuración antes de ejecutar S2-05.

Este script verifica:
1. API key configurada correctamente
2. Acceso a OpenAI funcional
3. Flow T-A-S ejecuta correctamente
4. Budget monitoring funciona
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Cargar .env
load_dotenv()

print("=" * 70)
print(" S2-05 PRE-FLIGHT CHECK")
print("=" * 70)

# 1. Verificar API key
print("\n1️⃣  Checking API Key...")
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("   ❌ DEEPSEEK_API_KEY not found in environment")
    sys.exit(1)
else:
    print(f"   ✅ API Key found (length: {len(api_key)} chars)")
    print(f"   Key starts with: {api_key[:7]}...")

# 2. Test DeepSeek connection
print("\n2️⃣  Testing DeepSeek Connection...")
try:
    from openai import OpenAI

    # Point client to DeepSeek endpoint
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    # Hacer una llamada simple
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "Say 'test successful' in exactly two words."}],
        max_tokens=10,
        temperature=0.0,
    )

    result = response.choices[0].message.content.strip()
    print(f"   ✅ DeepSeek API responding: '{result}'")
    print(f"   📊 Tokens used: {response.usage.total_tokens}")

except Exception as e:
    print(f"   ❌ Error connecting to DeepSeek: {e}")
    sys.exit(1)

# 3. Test budget monitor
print("\n3️⃣  Testing Budget Monitor...")
try:
    sys.path.append(str(Path(__file__).parent / "src"))
    from utils.budget_monitor import BudgetStatus, TokenUsage, check_item_token_cap

    # Test token cap
    usage = TokenUsage("test-001", 3000, 4000, 7000, 0.5)
    within_cap = check_item_token_cap(usage)
    print(f"   ✅ Token cap check: 7000 tokens - {within_cap and 'Within' or 'Exceeds'} cap")

    # Test budget status
    status = BudgetStatus(
        run_id="test",
        total_items=200,
        processed_items=1,
        total_tokens=7000,
        total_cost_usd=0.5,
        budget_limit_usd=100.0,
    )
    print(f"   ✅ Budget status: {status.budget_used_pct:.1f}% used")

except Exception as e:
    print(f"   ❌ Error testing budget monitor: {e}")
    sys.exit(1)

# 4. Test T-A-S flow on one problem
print("\n4️⃣  Testing T-A-S Flow on Sample Problem...")
try:
    from flows.tas import TASFlowConfig, run_tas_k1

    # Simple test problem
    test_problem = {
        "problem_id": "test-001",
        "question": "If John has 5 apples and gives 2 to Mary, how many apples does John have left?",  # noqa: E501
        "answer": "John has 5 - 2 = 3 apples left. #### 3",
    }

    config = TASFlowConfig(
        run_id="test-run",
        seed=42,
        dataset_name="gsm8k",
        model_name="deepseek-chat",
    )

    print(f"   Running T-A-S on: {test_problem['question'][:60]}...")
    result = run_tas_k1(test_problem, config)

    # Verificar resultado
    if "thesis" in result and "antithesis" in result and "synthesis" in result:
        print("   ✅ T-A-S completed successfully")
        print(f"   📝 Thesis answer: {result['thesis']['answer'][:50]}...")
        print(f"   📝 Synthesis answer: {result['synthesis']['answer'][:50]}...")

        # Calcular tokens totales
        total_tokens = 0
        for stage in [result["thesis"], result["antithesis"], result["synthesis"]]:
            if "meta" in stage and "usage" in stage["meta"]:
                total_tokens += stage["meta"]["usage"].get("total_tokens", 0)
        print(f"   📊 Total tokens: {total_tokens:,}")
    else:
        print("   ⚠️  Warning: Unexpected result structure")
        print(f"   Keys: {list(result.keys())}")

except Exception as e:
    print(f"   ❌ Error testing T-A-S flow: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# 5. Check dataset IDs file
print("\n5️⃣  Checking Dataset IDs...")
try:
    import json

    ids_file = Path("data/processed/gsm8k_s1_200_seed42_ids.json")
    if not ids_file.exists():
        print(f"   ❌ IDs file not found: {ids_file}")
        sys.exit(1)

    with open(ids_file) as f:
        data = json.load(f)

    print(f"   ✅ IDs file found: {len(data['ids'])} problems")
    print(f"   Seed: {data['seed']}, Hash: {data['content_hash']}")

except Exception as e:
    print(f"   ❌ Error checking dataset IDs: {e}")
    sys.exit(1)

# Success!
print("\n" + "=" * 70)
print("✅ ALL CHECKS PASSED - READY TO RUN S2-05")
print("=" * 70)
print("\nYou can now run:")
print("  python run_s2_05_tas_200.py")
print("\nEstimated time: 2-3 hours for 200 problems")
print("Estimated cost: ~$30-50 (depends on problem complexity)")
print()
