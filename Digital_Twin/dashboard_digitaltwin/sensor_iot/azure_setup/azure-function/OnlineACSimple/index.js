/**
 * Simple Online AC Recommendation - Debug Version
 */

module.exports = async function (context, req) {
    context.res = {
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    };

    try {
        const action = req.params.action || 'predict';

        context.log.info(`[OnlineAC] Action: ${action}`);

        switch (action) {
            case 'predict':
                const { suhu, kelembaban, daya, jumlahOrang, jam } = req.body || {};

                const hour = jam !== undefined ? jam : new Date().getHours();
                const orang = jumlahOrang || 0;
                const power = daya || 0;
                const humid = kelembaban || 50;
                const temp = suhu || 25;

                // Simple prediction
                let recommended = 24.0;
                if (temp > 25) recommended += (temp - 25) * -0.3;
                if (humid > 60) recommended += (humid - 60) * -0.01;
                if (power > 100) recommended += (power - 100) * -0.001;
                if (hour >= 8 && hour <= 17) recommended -= 0.5;
                if (orang > 0) recommended -= orang / 20;
                recommended = Math.max(18, Math.min(28, recommended));

                context.res.body = {
                    success: true,
                    data: {
                        recommendedTemp: Math.round(recommended * 10) / 10,
                        comfortLevel: recommended <= 21 ? "COOL" : recommended <= 25 ? "COMFORTABLE" : "WARM",
                        confidence: 0.85,
                        online_learning: true,
                        data_count: 0,
                        timestamp: new Date().toISOString()
                    }
                };
                break;

            case 'status':
                context.res.body = {
                    success: true,
                    data: {
                        status: "running",
                        online_learning: true,
                        version: "1.0-simplified"
                    }
                };
                break;

            default:
                context.res.status = 400;
                context.res.body = { error: "Invalid action" };
        }
    } catch (error) {
        context.log.error("[OnlineAC] Error:", error);
        context.res.status = 500;
        context.res.body = { error: error.message };
    }
};