# -*- coding: utf-8 -*-
"""
导入A股列表到stock_pool表
"""

import sys
import os
import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db_helper import get_db_connection


def import_stocks_from_csv():
    """从CSV导入股票数据"""
    print("\n" + "=" * 60)
    print("📥 导入A股列表")
    print("=" * 60)

    csv_path = "data/stock_basic.csv"

    try:
        # 读取CSV文件
        print(f"\n1️⃣ 读取CSV文件: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8')

        print(f"   文件包含 {len(df)} 条记录")
        print(f"   列: {', '.join(df.columns)}")

        # 显示前几条数据
        print("\n2️⃣ 数据示例:")
        print(df.head(3).to_string(index=False))

        # 导入数据库
        print("\n3️⃣ 开始导入数据库...")
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 清空现有数据
            cursor.execute("DELETE FROM stock_pool")
            conn.commit()
            print(f"   ✅ 已清空现有数据")

            # 批量插入
            success_count = 0
            for _, row in df.iterrows():
                try:
                    cursor.execute("""
                        INSERT INTO stock_pool
                        (ts_code, symbol, stock_name, area, industry, list_date)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        row['ts_code'],
                        row['symbol'],
                        row['name'],
                        row.get('area', ''),
                        row.get('industry', ''),
                        row.get('list_date', '')
                    ))
                    success_count += 1
                except Exception as e:
                    print(f"   ❌ 插入失败 {row['ts_code']}: {e}")

            conn.commit()

            print(f"\n4️⃣ 导入完成！")
            print(f"   ✅ 成功导入: {success_count} 条")
            print(f"   ❌ 失败: {len(df) - success_count} 条")

            # 验证导入结果
            cursor.execute("SELECT COUNT(*) as total FROM stock_pool")
            total = cursor.fetchone()['total']
            print(f"\n5️⃣ 验证结果:")
            print(f"   数据库中现有 {total} 条记录")

            # 显示部分导入的数据
            cursor.execute("""
                SELECT ts_code, symbol, stock_name, area, industry, list_date
                FROM stock_pool
                LIMIT 5
            """)
            records = cursor.fetchall()

            print(f"\n6️⃣ 导入数据示例:")
            for r in records:
                print(f"   {r['ts_code']} | {r['symbol']:6s} | {r['stock_name']:8s} | {r['area']:4s} | {r['industry']:4s} | {r['list_date']}")

        print("\n✅ 导入完成！")
        return True

    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 A股列表导入工具")
    print("=" * 60)

    # 导入数据
    if import_stocks_from_csv():
        print("\n" + "=" * 60)
        print("🎉 所有操作完成！")
        print("=" * 60)
    else:
        print("\n❌ 导入过程中出现错误")


if __name__ == "__main__":
    main()
