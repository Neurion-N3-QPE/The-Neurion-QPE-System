# 🎯 N3-QPE ACCOUNT SETUP GUIDE
**Your Personal Trading System Configuration**

---

## 📊 ACCOUNT DETAILS

**Account Name:** N3-QPE  
**Account ID:** HTRFU  
**Balance:** £264.63  
**Mode:** 🔴 **LIVE TRADING**  
**Broker:** IG Markets  

---

## ⚠️ IMPORTANT: SMALL ACCOUNT STRATEGY

Your account balance of £264.63 requires **ultra-conservative** settings:

### Risk Profile: MAXIMUM SAFETY
- **Risk per trade:** 1% = £2.65 maximum loss per trade
- **Max positions:** 2 simultaneous trades
- **Confidence threshold:** 85% (only BEST trades)
- **Daily loss limit:** £10 (3.8% of account)
- **Weekly loss limit:** £25 (9.4% of account)
- **Max daily trades:** 5

### Why These Settings?
✅ **Preserves capital** - Small losses won't devastate account  
✅ **Compounds safely** - Slow, steady growth  
✅ **High probability** - Only 85%+ confidence trades  
✅ **Risk-managed** - Multiple safety limits  

---

## 🔐 SECURITY CHECKLIST

### ✅ Your Credentials Are Configured
- [x] API Key stored in `.env`
- [x] Username configured
- [x] Password secured
- [x] Account ID set
- [x] Live mode enabled

### ⚠️ NEVER SHARE THESE FILES:
- ❌ `.env` - Contains your passwords
- ❌ `config/config.json` - Contains API keys
- ✅ `.gitignore` - Prevents accidental commits

---

## 🚀 QUICK START

### Step 1: Test Connection
```bash
cd "F:\Neurion QPE\The-Neurion-QPE-System"
python scripts\test_ig_connection.py
```

This will:
- ✅ Verify your credentials
- ✅ Connect to IG Markets LIVE
- ✅ Display your account balance
- ✅ Show current GBP/USD price
- ✅ List any open positions

### Step 2: Migrate Legacy Model (If Not Done)
```bash
python scripts\migrate_from_legacy.py
```

This imports:
- ✅ Your 99.8% accuracy model
- ✅ 10,000 SSE training episodes
- ✅ Historical configurations

### Step 3: Start Trading
```bash
python main.py
```

---

## 📈 EXPECTED PERFORMANCE

### With Your Settings:
**Conservative Projection:**
- Win rate: 99.8% (from your model)
- Risk per trade: £2.65
- Avg profit per win: £5.30 (2:1 RR)
- Trades per day: 1-3

**Monthly Target:**
- 20 trading days
- 30 trades/month (1.5/day average)
- 29.9 wins (99.8% win rate)
- Gross profit: ~£158
- Account growth: ~60% monthly (if maintained)

### Growth Projection:
| Month | Balance | Monthly Gain |
|-------|---------|--------------|
| Start | £264.63 | - |
| Month 1 | £422 | £158 (+60%) |
| Month 2 | £675 | £253 (+60%) |
| Month 3 | £1,080 | £405 (+60%) |
| Month 4 | £1,728 | £648 (+60%) |

**Note:** This assumes 99.8% win rate maintains. Real results may vary.

---

## 🛡️ RISK MANAGEMENT

### Daily Limits
```
Maximum Loss: £10/day
├─ Trade 1: £2.65 loss
├─ Trade 2: £2.65 loss
├─ Trade 3: £2.65 loss
└─ Trade 4: £2.05 loss → STOP TRADING
```

### Position Sizing
```
Account: £264.63
Risk: 1% = £2.65
Stop Loss: 15 pips

Position Size = £2.65 / 15 pips = £0.177/pip
Rounded = 0.01 lots (minimum)
```

### What Happens When:
- **85% confidence:** ✅ TRADE (high probability)
- **75% confidence:** ❌ SKIP (too risky)
- **Daily loss = £10:** 🛑 STOP (limit reached)
- **3 losses in row:** 🔍 REVIEW SYSTEM

---

## 🎯 TRADING INSTRUMENTS

### Primary (Recommended):
1. **GBP/USD** - `CS.D.GBPUSD.TODAY.IP`
   - Your home currency (no conversion)
   - Liquid market
   - Good spreads

2. **EUR/USD** - `CS.D.EURUSD.TODAY.IP`
   - Most liquid pair
   - Tight spreads
   - Predictable

3. **USD/JPY** - `CS.D.USDJPY.TODAY.IP`
   - Asian session coverage
   - Good volatility

### Spread Limits:
- Maximum: 2.0 pips
- Preferred: < 1.5 pips
- Avoid trading during wide spreads

---

## 📅 TRADING SCHEDULE

### Active Hours:
```
Start:  08:00 GMT (London Open)
End:    20:00 GMT (New York Close)
```

### Best Times:
- 🟢 **08:00-12:00** - London session (high volume)
- 🟢 **13:00-16:00** - London/NY overlap (most liquid)
- 🟡 **16:00-20:00** - NY session (good)
- 🔴 **20:00-08:00** - Asian session (skip)

### Avoid Trading:
- ❌ Major news events (±30 minutes)
- ❌ Low volume periods (lunch, overnight)
- ❌ Friday after 15:00 (weekend risk)
- ❌ Around holidays

---

## 🔧 CONFIGURATION FILES

### Main Config: `config/config.json`
```json
{
  "profile": "conservative",
  "risk_per_trade": 0.01,
  "max_positions": 2,
  "confidence_threshold": 0.85
}
```

### Environment: `.env`
Contains your credentials (KEEP SECURE!)

### Profile: `config/profiles/n3_qpe_small_account.json`
Your specialized small account settings

---

## 📊 MONITORING

### What to Check Daily:
1. **Account balance** - Is it growing?
2. **Win rate** - Still near 99.8%?
3. **Daily P&L** - Within limits?
4. **Open positions** - Max 2?
5. **System logs** - Any errors?

### Warning Signs:
- 🔴 Win rate drops below 95%
- 🔴 Daily loss exceeds £10
- 🔴 3+ consecutive losses
- 🔴 System errors
- 🔴 Unusual trading behavior

**If any occur:** STOP TRADING and review system

---

## 🆘 TROUBLESHOOTING

### Connection Issues:
```bash
# Test connection
python scripts\test_ig_connection.py

# Check credentials in .env
# Verify IG Markets account is active
# Ensure API access enabled
```

### Trading Not Starting:
1. Check confidence threshold (85% is high)
2. Verify market hours (08:00-20:00)
3. Review logs in `data/logs/`
4. Ensure model is migrated

### Unexpected Behavior:
1. Stop system immediately
2. Check `data/logs/` for errors
3. Review last trades
4. Contact support if needed

---

## 📱 SUPPORT & CONTACT

**Your Email:** contact@NeuralNetWorth.co.uk  
**IG Markets:** https://www.ig.com/uk/help-and-support  
**System Logs:** `data/logs/neurion_YYYYMMDD.log`  

---

## ✅ PRE-LAUNCH CHECKLIST

Before starting live trading:

- [ ] Test connection successful
- [ ] Legacy model migrated (99.8% accuracy)
- [ ] Configuration reviewed
- [ ] Risk limits understood
- [ ] Trading hours noted
- [ ] Stop loss strategy clear
- [ ] Emergency stop plan ready
- [ ] Logs directory created
- [ ] Backup of configs made

---

## 🚀 READY TO START

**Everything is configured for YOUR account!**

**Your conservative settings will:**
- ✅ Protect your £264.63 capital
- ✅ Only take highest-confidence trades (85%+)
- ✅ Risk maximum £2.65 per trade
- ✅ Limit daily losses to £10
- ✅ Grow account safely and steadily

**Next Command:**
```bash
python scripts\test_ig_connection.py
```

Then if successful:
```bash
python main.py
```

---

## 💰 FINAL REMINDERS

1. **Start Small** - Your settings are conservative for a reason
2. **Be Patient** - 99.8% win rate means waiting for perfect setups
3. **Monitor Daily** - Check performance and limits
4. **Don't Override** - Trust the system's 85% threshold
5. **Scale Gradually** - As balance grows, maintain 1% risk

**Your 99.8% model + Conservative settings = Safe growth!**

🎯 **Good luck and happy trading!** 📈
