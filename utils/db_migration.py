# -*- coding: utf-8 -*-
"""
数据库迁移工具
用于添加新的技术指标字段
"""

import sqlite3
import config


def migrate_add_extended_indicators():
    """
    添加扩展技术指标字段到 stock_indicators 表

    返回:
        bool: 是否成功
    """
    print("正在添加扩展技术指标字段...")

    try:
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='stock_indicators'
        """)
        if not cursor.fetchone():
            print("❌ stock_indicators 表不存在，请先初始化数据库")
            return False

        # 获取现有列
        cursor.execute("PRAGMA table_info(stock_indicators)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # 定义需要添加的新列
        new_columns = [
            # 历史高低点
            ("max_high_5d", "REAL"),
            ("max_high_10d", "REAL"),
            ("max_high_20d", "REAL"),
            ("max_high_60d", "REAL"),
            ("max_low_5d", "REAL"),
            ("max_low_10d", "REAL"),
            ("max_low_20d", "REAL"),
            ("max_low_60d", "REAL"),

            # 前一日数据
            ("prev_close", "REAL"),
            ("prev_high", "REAL"),
            ("prev_low", "REAL"),
            ("prev_volume", "REAL"),
            ("prev_change_pct", "REAL"),

            # 连续统计
            ("consecutive_up_days", "INTEGER"),
            ("consecutive_down_days", "INTEGER"),

            # K线形态
            ("body", "REAL"),
            ("body_ratio", "REAL"),
            ("upper_shadow", "REAL"),
            ("lower_shadow", "REAL"),
            ("upper_shadow_ratio", "REAL"),
            ("lower_shadow_ratio", "REAL"),

            # 位置指标
            ("position_20d", "REAL"),
            ("position_60d", "REAL"),
        ]

        # 添加不存在的列
        added_count = 0
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE stock_indicators ADD COLUMN {col_name} {col_type}")
                    print(f"  ✅ 添加列: {col_name}")
                    added_count += 1
                except Exception as e:
                    print(f"  ❌ 添加列失败 {col_name}: {e}")
            else:
                print(f"  ℹ️  列已存在: {col_name}")

        conn.commit()
        conn.close()

        print(f"\n✅ 迁移完成！共添加 {added_count} 个新列")
        return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False


def check_migration_status():
    """
    检查扩展指标字段的迁移状态

    返回:
        dict: 迁移状态信息
    """
    required_columns = [
        "max_high_5d", "max_high_10d", "max_high_20d", "max_high_60d",
        "max_low_5d", "max_low_10d", "max_low_20d", "max_low_60d",
        "prev_close", "prev_high", "prev_low", "prev_volume", "prev_change_pct",
        "consecutive_up_days", "consecutive_down_days",
        "body", "body_ratio", "upper_shadow", "lower_shadow",
        "upper_shadow_ratio", "lower_shadow_ratio",
        "position_20d", "position_60d"
    ]

    try:
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(stock_indicators)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        conn.close()

        missing = [col for col in required_columns if col not in existing_columns]

        return {
            "status": "OK" if not missing else "PENDING",
            "total_required": len(required_columns),
            "existing": len([col for col in required_columns if col in existing_columns]),
            "missing": missing
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e)
        }


if __name__ == "__main__":
    print("=" * 60)
    print("扩展技术指标数据库迁移")
    print("=" * 60)

    # 检查当前状态
    print("\n1. 检查迁移状态...")
    status = check_migration_status()
    print(f"   状态: {status['status']}")
    print(f"   已有字段: {status.get('existing', 0)}/{status.get('total_required', 0)}")

    if status.get("missing"):
        print(f"   缺失字段: {', '.join(status['missing'][:5])}{'...' if len(status['missing']) > 5 else ''}")

    # 执行迁移
    print("\n2. 执行迁移...")
    if migrate_add_extended_indicators():
        print("\n3. 验证迁移结果...")
        status = check_migration_status()
        print(f"   状态: {status['status']}")
        print(f"   已有字段: {status.get('existing', 0)}/{status.get('total_required', 0)}")

        if status['status'] == 'OK':
            print("\n✅ 所有扩展指标字段已成功添加！")
        else:
            print(f"\n⚠️  仍有 {len(status.get('missing', []))} 个字段未添加")
    else:
        print("\n❌ 迁移失败")

    print("\n" + "=" * 60)
