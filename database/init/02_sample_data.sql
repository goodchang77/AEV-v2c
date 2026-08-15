-- =====================================================
-- 台股前50大公司基礎資料初始化
-- Taiwan Stock Market Top 50 Companies Sample Data
-- =====================================================

-- 插入台股前50大公司基本資料
INSERT INTO companies (company_id, company_name, company_name_en, industry_code, industry_name, market_type, listing_date, capital_amount, outstanding_shares, par_value) VALUES
-- 電子科技類
('2330', '台積電', 'Taiwan Semiconductor Manufacturing Company Limited', 'M2300', '半導體業', '上市', '1994-09-05', 2593037230, 25930372299, 10.00),
('2317', '鴻海', 'Hon Hai Precision Industry Co., Ltd.', 'M2300', '電腦及週邊設備業', '上市', '1991-06-05', 1386691208, 13866912080, 10.00),
('2454', '聯發科', 'MediaTek Inc.', 'M2300', '半導體業', '上市', '2001-07-23', 15931020, 1593102058, 10.00),
('2382', '廣達', 'Quanta Computer Inc.', 'M2300', '電腦及週邊設備業', '上市', '1999-06-25', 35169717, 3516971692, 10.00),
('3008', '大立光', 'Largan Precision Co., Ltd.', 'M2300', '光電業', '上市', '2002-07-03', 1390000, 139028050, 10.00),
('2308', '台達電', 'Delta Electronics, Inc.', 'M2300', '電機機械', '上市', '1988-09-28', 26014969, 2601496892, 10.00),
('6505', '台塑化', 'Formosa Petrochemical Corporation', 'M1700', '石油及煤製品業', '上市', '2010-10-12', 146409854, 14640985448, 10.00),
('2603', '長榮', 'Evergreen Marine Corporation', 'H', '航運業', '上市', '1987-03-16', 25027013, 2502701303, 10.00),

-- 金融保險類
('2880', '華南金', 'Hua Nan Financial Holdings Co., Ltd.', 'J', '金融保險業', '上市', '2001-12-19', 123344012, 12334401243, 10.00),
('2881', '富邦金', 'Fubon Financial Holding Co., Ltd.', 'J', '金融保險業', '上市', '2001-12-19', 107725989, 10772598909, 10.00),
('2882', '國泰金', 'Cathay Financial Holding Co., Ltd.', 'J', '金融保險業', '上市', '2001-12-19', 107644804, 10764480421, 10.00),
('2883', '開發金', 'China Development Financial Holding Corporation', 'J', '金融保險業', '上市', '2001-12-19', 120435860, 12043586039, 10.00),
('2884', '玉山金', 'E.SUN Financial Holding Co., Ltd.', 'J', '金融保險業', '上市', '2002-02-01', 89862717, 8986271747, 10.00),
('2885', '元大金', 'Yuanta Financial Holding Co., Ltd.', 'J', '金融保險業', '上市', '2002-02-01', 116097172, 11609717202, 10.00),
('2886', '兆豐金', 'Mega Financial Holding Co., Ltd.', 'J', '金融保險業', '上市', '2002-02-01', 103678641, 10367864147, 10.00),
('2887', '台新金', 'Taishin Financial Holding Co., Ltd.', 'J', '金融保險業', '上市', '2002-02-01', 89887773, 8988777312, 10.00),
('2888', '新光金', 'Shin Kong Financial Holding Co., Ltd.', 'J', '金融保險業', '上市', '2002-02-01', 95799946, 9579994647, 10.00),
('2890', '永豐金', 'SinoPac Financial Holdings Co., Ltd.', 'J', '金融保險業', '上市', '2002-02-01', 82699011, 8269901161, 10.00),
('2891', '中信金', 'CTBC Financial Holding Co., Ltd.', 'J', '金融保險業', '上市', '2002-02-01', 101070166, 10107016646, 10.00),
('2892', '第一金', 'First Financial Holding Co., Ltd.', 'J', '金融保險業', '上市', '2002-02-01', 89705924, 8970592440, 10.00),

-- 傳統產業類
('1301', '台塑', 'Formosa Plastics Corporation', 'M1700', '塑膠工業', '上市', '1962-02-09', 76934842, 7693484232, 10.00),
('1303', '南亞', 'Nan Ya Plastics Corporation', 'M1700', '塑膠工業', '上市', '1973-02-03', 98643476, 9864347617, 10.00),
('1326', '台化', 'Formosa Chemicals & Fibre Corporation', 'M1700', '化學工業', '上市', '1967-02-11', 97635721, 9763572143, 10.00),
('2002', '中鋼', 'China Steel Corporation', 'M2100', '鋼鐵工業', '上市', '1985-12-11', 150475094, 15047509415, 10.00),
('2207', '和泰車', 'Hotai Motor Co., Ltd.', 'G', '汽車工業', '上市', '1986-11-28', 4558764, 455876432, 10.00),
('2303', '聯電', 'United Microelectronics Corporation', 'M2300', '半導體業', '上市', '1985-05-03', 131421938, 13142193830, 10.00),
('2312', '華碩', 'ASUSTeK Computer Inc.', 'M2300', '電腦及週邊設備業', '上市', '1996-02-15', 7627508, 762750821, 10.00),
('2324', '仁寶', 'Compal Electronics, Inc.', 'M2300', '電腦及週邊設備業', '上市', '1998-10-29', 22066204, 2206620439, 10.00),
('2357', '華碩電腦', 'ASUSTeK Computer Inc.', 'M2300', '電腦及週邊設備業', '上市', '1996-02-15', 7627508, 762750821, 10.00),

-- 民生消費類
('1216', '統一', 'Uni-President Enterprises Corporation', 'I', '食品工業', '上市', '1967-07-26', 34837801, 3483780117, 10.00),
('1101', '台泥', 'Taiwan Cement Corporation', 'M2500', '水泥工業', '上市', '1962-02-09', 74436000, 7443600000, 10.00),
('1102', '亞泥', 'Asia Cement Corporation', 'M2500', '水泥工業', '上市', '1973-01-30', 41100000, 4110000000, 10.00),
('2105', '正新', 'Cheng Shin Rubber Ind. Co., Ltd.', 'M1900', '橡膠工業', '上市', '1988-07-28', 14460000, 1446000000, 10.00),
('2474', '可成', 'Catcher Technology Co., Ltd.', 'M2300', '其他電子業', '上市', '2004-11-25', 2677426, 267742659, 10.00),
('2498', '宏達電', 'HTC Corporation', 'M2300', '通信網路業', '上市', '2002-03-15', 8249550, 824955026, 10.00),

-- 生技醫療類
('4904', '遠傳', 'Far EasTone Telecommunications Co., Ltd.', 'M2900', '通信網路業', '上市', '2001-08-20', 36866289, 3686628926, 10.00),
('3045', '台灣大', 'Taiwan Mobile Co., Ltd.', 'M2900', '通信網路業', '上市', '2000-08-18', 26000000, 2600000000, 10.00),

-- 綠能環保類
('6415', '矽力-KY', 'Silergy Corp.', 'M2300', '半導體業', '上市', '2017-01-09', 1300000, 129994920, 10.00),

-- 營建類
('2547', '日勝生', 'RSEA Engineering Corporation', 'M3100', '營建業', '上市', '1993-12-09', 8700000, 870000000, 10.00),
('9904', '寶成', 'Pou Chen Corporation', 'CA', '其他業', '上市', '1989-02-28', 23100000, 2310000000, 10.00),

-- REITs & 其他
('2609', '陽明', 'Yang Ming Marine Transport Corporation', 'H', '航運業', '上市', '1974-12-14', 37100000, 3710000000, 10.00),
('2610', '華航', 'China Airlines Ltd.', 'H', '航運業', '上市', '1998-10-26', 60477024, 6047702429, 10.00),

-- 觀光類
('2634', '漢翔', 'Aerospace Industrial Development Corporation', 'M2000', '航太工業', '上市', '2014-09-26', 14500000, 1450000000, 10.00),
('2615', '萬海', 'Wan Hai Lines Ltd.', 'H', '航運業', '上市', '1999-02-11', 14385877, 1438587705, 10.00),

-- 食品飲料類
('1227', '佳格', 'Standard Foods Corporation', 'I', '食品工業', '上市', '1990-04-27', 3120000, 312000000, 10.00),
('1229', '聯華', 'Lien Hwa Industrial Corporation', 'I', '食品工業', '上市', '1971-10-07', 7200000, 720000000, 10.00),

-- 紡織類
('1409', '新纖', 'Far Eastern New Century Corporation', 'M1400', '纺織纤維', '上市', '1967-10-20', 23513000, 2351300000, 10.00),
('1402', '遠東新', 'Far Eastern New Century Corporation', 'M1400', '紡織纖維', '上市', '1967-10-20', 23513000, 2351300000, 10.00),

-- 其他重要公司
('9910', '豐泰', 'Feng Tay Enterprises Co., Ltd.', 'CA', '其他業', '上市', '1988-11-29', 4070000, 407000000, 10.00),
('4938', '和碩', 'Pegatron Corporation', 'M2300', '電腦及週邊設備業', '上市', '2010-06-17', 35800000, 3580000000, 10.00);

-- 更新公司狀態為活躍
UPDATE companies SET is_active = true WHERE company_id IN (
    '2330', '2317', '2454', '2382', '3008', '2308', '6505', '2603',
    '2880', '2881', '2882', '2883', '2884', '2885', '2886', '2887', '2888', '2890', '2891', '2892',
    '1301', '1303', '1326', '2002', '2207', '2303', '2312', '2324', '2357',
    '1216', '1101', '1102', '2105', '2474', '2498',
    '4904', '3045',
    '6415',
    '2547', '9904',
    '2609', '2610',
    '2634', '2615',
    '1227', '1229',
    '1409', '1402',
    '9910', '4938'
);

-- 創建管理員用戶
INSERT INTO users (username, email, password_hash, full_name, role, is_active, is_verified) VALUES
('admin', 'admin@financial-analysis.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewMxtCdxLuJw4vJu', '系統管理員', 'admin', true, true),
('analyst', 'analyst@financial-analysis.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewMxtCdxLuJw4vJu', '財務分析師', 'analyst', true, true),
('demo_user', 'demo@financial-analysis.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewMxtCdxLuJw4vJu', '示範用戶', 'user', true, true);

-- 為示範用戶創建追蹤清單
INSERT INTO user_watchlists (user_id, company_id, watchlist_name, notes, priority)
SELECT 
    u.user_id,
    c.company_id,
    'Taiwan Top 10',
    CASE 
        WHEN c.company_id = '2330' THEN '全球最大半導體製造商'
        WHEN c.company_id = '2317' THEN '全球最大電子製造服務商'
        WHEN c.company_id = '2454' THEN '全球無線通信及數位多媒體晶片設計領導廠商'
        WHEN c.company_id = '2881' THEN '台灣領先金融控股公司'
        WHEN c.company_id = '2882' THEN '台灣最大產險公司母公司'
        ELSE '重要投資標的'
    END,
    CASE 
        WHEN c.company_id IN ('2330', '2317', '2454') THEN 1
        ELSE 0
    END
FROM users u
CROSS JOIN companies c
WHERE u.username = 'demo_user'
AND c.company_id IN ('2330', '2317', '2454', '2881', '2882', '1301', '2002', '1216', '3008', '2308');

-- 插入產業基準資料範例 (2024Q3)
INSERT INTO industry_benchmarks (industry_code, year_quarter, company_count, avg_roe, avg_roa, avg_current_ratio, avg_debt_ratio, avg_gross_margin, avg_operating_margin, avg_net_margin, avg_pe_ratio, avg_pb_ratio) VALUES
('M2300', '2024Q3', 25, 0.1850, 0.0920, 2.15, 0.35, 0.4200, 0.1800, 0.1500, 18.50, 2.80),
('J', '2024Q3', 15, 0.0920, 0.0085, 1.05, 0.88, 0.6500, 0.3200, 0.2800, 12.80, 1.15),
('M1700', '2024Q3', 8, 0.0650, 0.0420, 1.85, 0.42, 0.2800, 0.0950, 0.0750, 15.20, 1.25),
('I', '2024Q3', 12, 0.0780, 0.0510, 2.35, 0.38, 0.3500, 0.0850, 0.0680, 22.50, 1.65),
('H', '2024Q3', 6, 0.1250, 0.0680, 1.45, 0.52, 0.1500, 0.0680, 0.0550, 8.90, 1.05);

-- =====================================================
-- 建立系統監控視圖
-- =====================================================

-- 公司數量統計視圖
CREATE VIEW company_statistics AS
SELECT 
    market_type,
    COUNT(*) as total_companies,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_companies,
    COUNT(DISTINCT industry_code) as industry_count
FROM companies
GROUP BY market_type;

-- 用戶活動統計視圖
CREATE VIEW user_activity_stats AS
SELECT 
    role,
    COUNT(*) as total_users,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_users,
    COUNT(CASE WHEN last_login >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as users_active_30days
FROM users
GROUP BY role;

-- =====================================================
-- 資料初始化完成
-- =====================================================

-- 記錄初始化時間
-- 注意: market_type 受 CHECK 約束 (上市/上櫃/興櫃)，故標記列使用 '上市'
INSERT INTO companies (company_id, company_name, industry_code, market_type, is_active)
VALUES ('INIT', 'System Initialized', 'SYSTEM', '上市', false)
ON CONFLICT (company_id) DO UPDATE SET 
updated_at = CURRENT_TIMESTAMP;