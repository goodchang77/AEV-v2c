"""
同業比較分析
Peer Comparison Analysis

提供同業財務比率比較、產業基準分析和相對績效評估功能
"""

from typing import Dict, List, Optional, Tuple, Union
from decimal import Decimal
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
from statistics import median, mean

from src.core.logging import get_logger

logger = get_logger("peer_analysis")


class PerformanceRating(Enum):
    """績效評等"""
    EXCELLENT = "優秀"
    ABOVE_AVERAGE = "高於平均" 
    AVERAGE = "平均"
    BELOW_AVERAGE = "低於平均"
    POOR = "不佳"


@dataclass
class PeerCompanyData:
    """同業公司資料"""
    company_id: str
    company_name: str
    market_cap: float
    revenue: float
    net_income: float
    total_assets: float
    shareholders_equity: float
    
    # 關鍵比率
    roe: float
    roa: float
    current_ratio: float
    debt_ratio: float
    net_margin: float
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None


@dataclass 
class IndustryBenchmark:
    """產業基準"""
    industry_code: str
    industry_name: str
    company_count: int
    
    # 平均值
    avg_roe: float
    avg_roa: float
    avg_current_ratio: float
    avg_debt_ratio: float
    avg_gross_margin: float
    avg_net_margin: float
    avg_pe_ratio: float
    avg_pb_ratio: float
    
    # 中位數
    median_roe: float
    median_roa: float
    median_current_ratio: float
    median_debt_ratio: float
    
    # 分位數
    roe_25_percentile: float
    roe_75_percentile: float
    pe_25_percentile: float
    pe_75_percentile: float
    debt_25_percentile: float
    debt_75_percentile: float
    
    # 標準差
    roe_std_dev: float
    roa_std_dev: float


@dataclass
class PeerComparisonResult:
    """同業比較結果"""
    target_company_id: str
    industry_code: str
    peer_companies: List[PeerCompanyData]
    industry_benchmark: IndustryBenchmark
    
    # 目標公司在同業中的排名
    rankings: Dict[str, Dict[str, Union[int, float]]]
    
    # 績效評等
    performance_ratings: Dict[str, PerformanceRating]
    
    # 相對強弱分析
    strengths: List[str]
    weaknesses: List[str]
    
    # 改善建議
    recommendations: List[str]


class PeerAnalyzer:
    """同業比較分析器"""
    
    def __init__(self):
        self.key_ratios = [
            'roe', 'roa', 'current_ratio', 'debt_ratio', 
            'net_margin', 'pe_ratio', 'pb_ratio', 'ev_ebitda'
        ]
        
    def analyze_peer_comparison(self, 
                              target_company: PeerCompanyData,
                              peer_companies: List[PeerCompanyData],
                              industry_benchmark: IndustryBenchmark) -> PeerComparisonResult:
        """
        執行同業比較分析
        
        Args:
            target_company: 目標公司
            peer_companies: 同業公司列表
            industry_benchmark: 產業基準
            
        Returns:
            PeerComparisonResult: 比較分析結果
        """
        logger.calculation_log(
            company_id=target_company.company_id,
            calculation_type="peer_comparison",
            duration=0,
            success=False
        )
        
        try:
            # 1. 計算排名
            rankings = self._calculate_rankings(target_company, peer_companies)
            
            # 2. 評估績效等級
            performance_ratings = self._evaluate_performance(target_company, industry_benchmark)
            
            # 3. 分析優劣勢
            strengths, weaknesses = self._analyze_strengths_weaknesses(
                target_company, industry_benchmark, performance_ratings
            )
            
            # 4. 生成改善建議
            recommendations = self._generate_recommendations(weaknesses, target_company)
            
            result = PeerComparisonResult(
                target_company_id=target_company.company_id,
                industry_code=industry_benchmark.industry_code,
                peer_companies=peer_companies,
                industry_benchmark=industry_benchmark,
                rankings=rankings,
                performance_ratings=performance_ratings,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=recommendations
            )
            
            logger.calculation_log(
                company_id=target_company.company_id,
                calculation_type="peer_comparison",
                duration=0,
                success=True,
                peer_count=len(peer_companies)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"同業比較分析失敗: {e}")
            raise
    
    def _calculate_rankings(self, target_company: PeerCompanyData, 
                          peer_companies: List[PeerCompanyData]) -> Dict[str, Dict[str, Union[int, float]]]:
        """計算各項指標在同業中的排名"""
        rankings = {}
        all_companies = peer_companies + [target_company]
        
        for ratio in self.key_ratios:
            # 取得所有公司的該比率數值
            ratio_values = []
            for company in all_companies:
                value = getattr(company, ratio, None)
                if value is not None:
                    ratio_values.append((company.company_id, value))
            
            if not ratio_values:
                continue
                
            # 根據比率類型決定排序方向
            if ratio in ['debt_ratio']:  # 負面指標，越低越好
                ratio_values.sort(key=lambda x: x[1])
            else:  # 正面指標，越高越好
                ratio_values.sort(key=lambda x: x[1], reverse=True)
            
            # 找到目標公司排名
            target_rank = None
            target_value = None
            for idx, (company_id, value) in enumerate(ratio_values, 1):
                if company_id == target_company.company_id:
                    target_rank = idx
                    target_value = value
                    break
            
            if target_rank is not None:
                # 計算百分位數
                percentile = ((len(ratio_values) - target_rank + 1) / len(ratio_values)) * 100
                
                rankings[ratio] = {
                    'rank': target_rank,
                    'total': len(ratio_values),
                    'percentile': round(percentile, 1),
                    'value': target_value,
                    'best_in_peer': ratio_values[0][1],
                    'worst_in_peer': ratio_values[-1][1]
                }
        
        return rankings
    
    def _evaluate_performance(self, target_company: PeerCompanyData,
                            industry_benchmark: IndustryBenchmark) -> Dict[str, PerformanceRating]:
        """評估各項指標的績效等級"""
        ratings = {}
        
        # ROE 評估
        roe = target_company.roe
        if roe >= industry_benchmark.roe_75_percentile:
            ratings['roe'] = PerformanceRating.EXCELLENT
        elif roe >= industry_benchmark.avg_roe:
            ratings['roe'] = PerformanceRating.ABOVE_AVERAGE
        elif roe >= industry_benchmark.median_roe:
            ratings['roe'] = PerformanceRating.AVERAGE
        elif roe >= industry_benchmark.roe_25_percentile:
            ratings['roe'] = PerformanceRating.BELOW_AVERAGE
        else:
            ratings['roe'] = PerformanceRating.POOR
        
        # ROA 評估
        roa = target_company.roa
        if roa >= industry_benchmark.avg_roa + industry_benchmark.roa_std_dev:
            ratings['roa'] = PerformanceRating.EXCELLENT
        elif roa >= industry_benchmark.avg_roa:
            ratings['roa'] = PerformanceRating.ABOVE_AVERAGE
        elif roa >= industry_benchmark.median_roa:
            ratings['roa'] = PerformanceRating.AVERAGE
        elif roa >= industry_benchmark.avg_roa - industry_benchmark.roa_std_dev:
            ratings['roa'] = PerformanceRating.BELOW_AVERAGE
        else:
            ratings['roa'] = PerformanceRating.POOR
        
        # 流動比率評估
        current_ratio = target_company.current_ratio
        if current_ratio >= industry_benchmark.avg_current_ratio * 1.2:
            ratings['current_ratio'] = PerformanceRating.EXCELLENT
        elif current_ratio >= industry_benchmark.avg_current_ratio:
            ratings['current_ratio'] = PerformanceRating.ABOVE_AVERAGE
        elif current_ratio >= industry_benchmark.median_current_ratio:
            ratings['current_ratio'] = PerformanceRating.AVERAGE
        elif current_ratio >= industry_benchmark.avg_current_ratio * 0.8:
            ratings['current_ratio'] = PerformanceRating.BELOW_AVERAGE
        else:
            ratings['current_ratio'] = PerformanceRating.POOR
        
        # 負債比率評估（越低越好）
        debt_ratio = target_company.debt_ratio
        if debt_ratio <= industry_benchmark.debt_25_percentile:
            ratings['debt_ratio'] = PerformanceRating.EXCELLENT
        elif debt_ratio <= industry_benchmark.median_debt_ratio:
            ratings['debt_ratio'] = PerformanceRating.ABOVE_AVERAGE
        elif debt_ratio <= industry_benchmark.avg_debt_ratio:
            ratings['debt_ratio'] = PerformanceRating.AVERAGE
        elif debt_ratio <= industry_benchmark.debt_75_percentile:
            ratings['debt_ratio'] = PerformanceRating.BELOW_AVERAGE
        else:
            ratings['debt_ratio'] = PerformanceRating.POOR
        
        # 淨利率評估
        net_margin = target_company.net_margin
        if net_margin >= industry_benchmark.avg_net_margin * 1.5:
            ratings['net_margin'] = PerformanceRating.EXCELLENT
        elif net_margin >= industry_benchmark.avg_net_margin:
            ratings['net_margin'] = PerformanceRating.ABOVE_AVERAGE
        elif net_margin >= industry_benchmark.avg_net_margin * 0.7:
            ratings['net_margin'] = PerformanceRating.AVERAGE
        elif net_margin >= industry_benchmark.avg_net_margin * 0.5:
            ratings['net_margin'] = PerformanceRating.BELOW_AVERAGE
        else:
            ratings['net_margin'] = PerformanceRating.POOR
        
        # PE比率評估（如果有資料）
        if target_company.pe_ratio is not None and industry_benchmark.avg_pe_ratio > 0:
            pe_ratio = target_company.pe_ratio
            if industry_benchmark.pe_25_percentile <= pe_ratio <= industry_benchmark.pe_75_percentile:
                ratings['pe_ratio'] = PerformanceRating.AVERAGE
            elif pe_ratio < industry_benchmark.pe_25_percentile:
                ratings['pe_ratio'] = PerformanceRating.EXCELLENT  # 相對便宜
            elif pe_ratio < industry_benchmark.avg_pe_ratio:
                ratings['pe_ratio'] = PerformanceRating.ABOVE_AVERAGE
            elif pe_ratio < industry_benchmark.pe_75_percentile:
                ratings['pe_ratio'] = PerformanceRating.BELOW_AVERAGE
            else:
                ratings['pe_ratio'] = PerformanceRating.POOR  # 相對昂貴
        
        return ratings
    
    def _analyze_strengths_weaknesses(self, 
                                    target_company: PeerCompanyData,
                                    industry_benchmark: IndustryBenchmark,
                                    performance_ratings: Dict[str, PerformanceRating]) -> Tuple[List[str], List[str]]:
        """分析優勢與劣勢"""
        strengths = []
        weaknesses = []
        
        ratio_descriptions = {
            'roe': '股東權益報酬率',
            'roa': '資產報酬率', 
            'current_ratio': '流動比率',
            'debt_ratio': '負債比率',
            'net_margin': '淨利率',
            'pe_ratio': '本益比',
            'pb_ratio': '股價淨值比'
        }
        
        for ratio, rating in performance_ratings.items():
            description = ratio_descriptions.get(ratio, ratio)
            
            if rating in [PerformanceRating.EXCELLENT, PerformanceRating.ABOVE_AVERAGE]:
                if ratio == 'debt_ratio':
                    strengths.append(f"{description}控制良好，財務結構健全")
                elif ratio == 'pe_ratio':
                    strengths.append(f"{description}合理，投資價值佳")
                else:
                    strengths.append(f"{description}表現優異，高於產業平均")
            
            elif rating in [PerformanceRating.BELOW_AVERAGE, PerformanceRating.POOR]:
                if ratio == 'debt_ratio':
                    weaknesses.append(f"{description}偏高，需注意財務風險")
                elif ratio == 'pe_ratio':
                    weaknesses.append(f"{description}偏高，評價可能過高")
                elif ratio == 'current_ratio':
                    weaknesses.append(f"{description}偏低，短期償債能力有待改善")
                else:
                    weaknesses.append(f"{description}低於產業平均，有改善空間")
        
        # 市值規模分析
        if target_company.market_cap < 10_000_000_000:  # 100億以下
            strengths.append("中小型企業，具有成長潛力和靈活性")
        elif target_company.market_cap > 100_000_000_000:  # 1000億以上
            strengths.append("大型企業，具有市場領導地位和穩定性")
        
        return strengths, weaknesses
    
    def _generate_recommendations(self, weaknesses: List[str], 
                                target_company: PeerCompanyData) -> List[str]:
        """生成改善建議"""
        recommendations = []
        
        # 根據弱項生成具體建議
        weakness_keywords = ' '.join(weaknesses).lower()
        
        if '負債比率' in weakness_keywords or '財務風險' in weakness_keywords:
            recommendations.append("建議優化資本結構，降低負債比重，提升財務穩定性")
            recommendations.append("考慮透過現金流改善或股權融資來降低財務風險")
        
        if '流動比率' in weakness_keywords or '償債能力' in weakness_keywords:
            recommendations.append("加強現金流管理，提高短期償債能力")
            recommendations.append("檢討應收帳款與存貨周轉效率")
        
        if '股東權益報酬率' in weakness_keywords or 'roe' in weakness_keywords:
            recommendations.append("提升營運效率，改善獲利能力以提高股東報酬")
            recommendations.append("檢討資產配置效率，優化投資報酬率")
        
        if '資產報酬率' in weakness_keywords or 'roa' in weakness_keywords:
            recommendations.append("改善資產使用效率，提升資產創造收益能力")
            recommendations.append("檢討非核心資產，集中資源於核心業務")
        
        if '淨利率' in weakness_keywords:
            recommendations.append("加強成本控制，提升營運毛利率")
            recommendations.append("檢討產品組合，提高高毛利產品占比")
        
        if '本益比' in weakness_keywords and '偏高' in weakness_keywords:
            recommendations.append("當前估值可能偏高，建議投資人謹慎評估")
            recommendations.append("需持續關注營收成長以支撐現有評價水準")
        
        # 通用建議
        if len(recommendations) == 0:
            recommendations.append("持續監控財務指標變化，維持產業競爭優勢")
        
        recommendations.append("建議定期與同業標竿進行比較分析")
        recommendations.append("關注產業趨勢變化，適時調整營運策略")
        
        return recommendations[:5]  # 限制在5個建議內
    
    def calculate_composite_score(self, performance_ratings: Dict[str, PerformanceRating],
                                weights: Optional[Dict[str, float]] = None) -> float:
        """
        計算綜合評分
        
        Args:
            performance_ratings: 各項績效評等
            weights: 各項指標權重
            
        Returns:
            float: 綜合評分 (0-100)
        """
        if weights is None:
            # 預設權重
            weights = {
                'roe': 0.25,
                'roa': 0.20,
                'current_ratio': 0.15,
                'debt_ratio': 0.15,
                'net_margin': 0.15,
                'pe_ratio': 0.10
            }
        
        rating_scores = {
            PerformanceRating.EXCELLENT: 90,
            PerformanceRating.ABOVE_AVERAGE: 75,
            PerformanceRating.AVERAGE: 60,
            PerformanceRating.BELOW_AVERAGE: 45,
            PerformanceRating.POOR: 25
        }
        
        total_score = 0
        total_weight = 0
        
        for ratio, rating in performance_ratings.items():
            if ratio in weights:
                weight = weights[ratio]
                score = rating_scores[rating]
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def generate_peer_comparison_report(self, result: PeerComparisonResult) -> Dict[str, any]:
        """
        生成同業比較分析報告
        
        Args:
            result: 比較分析結果
            
        Returns:
            Dict: 結構化報告數據
        """
        # 計算綜合評分
        composite_score = self.calculate_composite_score(result.performance_ratings)
        
        # 統計績效分佈
        performance_distribution = {}
        for rating in PerformanceRating:
            count = sum(1 for r in result.performance_ratings.values() if r == rating)
            performance_distribution[rating.value] = count
        
        report = {
            'executive_summary': {
                'company_id': result.target_company_id,
                'industry': result.industry_code,
                'composite_score': round(composite_score, 1),
                'peer_count': len(result.peer_companies),
                'strengths_count': len(result.strengths),
                'weaknesses_count': len(result.weaknesses)
            },
            'performance_overview': {
                'ratings': {k: v.value for k, v in result.performance_ratings.items()},
                'distribution': performance_distribution
            },
            'ranking_analysis': result.rankings,
            'industry_comparison': {
                'industry_name': result.industry_benchmark.industry_name,
                'company_count': result.industry_benchmark.company_count,
                'key_benchmarks': {
                    'avg_roe': result.industry_benchmark.avg_roe,
                    'avg_roa': result.industry_benchmark.avg_roa,
                    'avg_current_ratio': result.industry_benchmark.avg_current_ratio,
                    'avg_debt_ratio': result.industry_benchmark.avg_debt_ratio
                }
            },
            'swot_analysis': {
                'strengths': result.strengths,
                'weaknesses': result.weaknesses,
                'recommendations': result.recommendations
            },
            'peer_companies': [
                {
                    'company_id': peer.company_id,
                    'company_name': peer.company_name,
                    'market_cap': peer.market_cap,
                    'key_ratios': {
                        'roe': peer.roe,
                        'roa': peer.roa,
                        'current_ratio': peer.current_ratio,
                        'debt_ratio': peer.debt_ratio
                    }
                }
                for peer in result.peer_companies
            ]
        }
        
        return report