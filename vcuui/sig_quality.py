
class SignalQuality_LTE:
    def __init__(self, rsrq, rsrp):
        self._rsrq = rsrq
        self._rsrp = rsrp

        q_rsrq = SignalQuality_LTE._rsrq_to_q(self._rsrq)
        q_rsrp = SignalQuality_LTE._rsrp_to_q(self._rsrp)

        # Weigh RSRQ 2x and RSRP 1x
        self._quality = (2.0 * q_rsrq + q_rsrp) / 3.0

    def quality(self):
        return self._quality

    @staticmethod
    def _rsrq_to_q(rsrq):
        """
        Maps LTE RSRQ to a 0..1 quality indicator
        - >= -10: 1.0 Excellent
        -  < -20: 0.2 Cell Edge
        - Values in between are linear interpolated
        """
        if rsrq > -10:
            q = 1.0
        elif rsrq < -20:
            q = 0.2
        else:
            q = 1+((rsrq+10)/10*0.8)

        return q

    @staticmethod
    def _rsrp_to_q(rsrp):
        """
        Maps LTE RSRP to a 0..1 quality indicator

        -  >= -80: 1.0 Excellent
        -  < -100: 0.2 Cell Edge
        - Values in between are linear interpolated
        """
        if rsrp > -80:
            q = 1.0
        elif rsrp < -100:
            q = 0.2
        else:
            q = 1+((rsrp+80)/20*0.8)

        return q
