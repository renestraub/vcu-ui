import math

from vcuui.sig_quality import SignalQuality_LTE


class TestLTE:
    def test_rsrq_1(self):
        q = SignalQuality_LTE._rsrq_to_q(0)
        assert(math.isclose(q, 1.0))

        q = SignalQuality_LTE._rsrq_to_q(-9.999)
        assert(math.isclose(q, 1.0))

        q = SignalQuality_LTE._rsrq_to_q(-10)
        assert(math.isclose(q, 1.0))

        q = SignalQuality_LTE._rsrq_to_q(-12.5)
        assert(math.isclose(q, 0.8))

        q = SignalQuality_LTE._rsrq_to_q(-15)
        assert(math.isclose(q, 0.6))

        q = SignalQuality_LTE._rsrq_to_q(-17.5)
        assert(math.isclose(q, 0.4))

        q = SignalQuality_LTE._rsrq_to_q(-20)
        assert(math.isclose(q, 0.20))

        q = SignalQuality_LTE._rsrq_to_q(-20.001)
        assert(math.isclose(q, 0.20))

        q = SignalQuality_LTE._rsrq_to_q(-30)
        assert(math.isclose(q, 0.20))

    def test_rsrp_1(self):
        q = SignalQuality_LTE._rsrp_to_q(0)
        assert(math.isclose(q, 1.0))

        q = SignalQuality_LTE._rsrp_to_q(-79.999)
        assert(math.isclose(q, 1.00))

        q = SignalQuality_LTE._rsrp_to_q(-80)
        assert(math.isclose(q, 1.00))

        q = SignalQuality_LTE._rsrp_to_q(-85)
        assert(math.isclose(q, 0.80))

        q = SignalQuality_LTE._rsrp_to_q(-90)
        assert(math.isclose(q, 0.60))

        q = SignalQuality_LTE._rsrp_to_q(-95)
        assert(math.isclose(q, 0.40))

        q = SignalQuality_LTE._rsrp_to_q(-100)
        assert(math.isclose(q, 0.20))

        q = SignalQuality_LTE._rsrp_to_q(-100.001)
        assert(math.isclose(q, 0.20))

        q = SignalQuality_LTE._rsrp_to_q(-140)
        assert(math.isclose(q, 0.20))

    def test_1(self):
        # Excellent
        lte_q = SignalQuality_LTE(-10, -80)
        q = lte_q.quality()
        assert(math.isclose(q, 1.0))

        # Cell edge - Close to disconnection
        lte_q = SignalQuality_LTE(-20, -100)
        q = lte_q.quality()
        assert(math.isclose(q, 0.2))
