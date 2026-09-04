import pytest
from sqlalchemy import text
from backend.app.database import engine

def test_postgresql_views_and_queries():
    """
    Executes PostgreSQL analytical views and reporting queries
    to verify SQL syntax and relational integrity.
    """
    with engine.connect() as conn:
        # 1. Test live center queue status view
        res1 = conn.execute(text("SELECT * FROM v_live_center_queue_status WHERE center_id = 1;")).fetchone()
        assert res1 is not None
        assert res1.center_name == "Central Procurement Center - Suryapet"
        assert res1.total_tokens_today >= 20

        # 2. Test farmer turn tracker view
        res2 = conn.execute(text("SELECT * FROM v_farmer_turn_tracker WHERE token_number = 'A023';")).fetchone()
        assert res2 is not None
        assert res2.farmer_name == "Ramesh Kumar Goud"
        assert res2.commodity_name == "Paddy / Rice (Grade-A)"
        assert res2.farmers_ahead >= 0

        # 3. Test procurement center analytics view
        res3 = conn.execute(text("SELECT * FROM v_procurement_center_analytics WHERE center_id = 1;")).fetchone()
        assert res3 is not None
        assert res3.total_transactions >= 10
        assert res3.total_procured_quintals > 0

        # 4. Test Aggregation with GROUP BY and HAVING
        query = text("""
            SELECT c.name, COUNT(pt.id) as txn_count, SUM(pt.net_weight_qtl) as total_weight
            FROM commodities c
            JOIN bookings b ON c.id = b.commodity_id
            JOIN procurement_transactions pt ON b.id = pt.booking_id
            GROUP BY c.name
            HAVING COUNT(pt.id) > 0;
        """)
        res4 = conn.execute(query).fetchall()
        assert len(res4) > 0
