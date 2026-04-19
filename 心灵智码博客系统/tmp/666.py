#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工业级产品表面缺陷检测系统（单文件版）
适用场景：金属/塑料零件表面缺陷（划痕、凹坑、污渍、裂纹）检测
配置说明：所有参数已定义在代码开头的CONFIG字典中，可直接修改
"""

import cv2
import numpy as np
import logging
import os
import time
import csv
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union

# ======================== 全局配置（直接修改此处参数） ========================
CONFIG = {
    # 预处理参数
    'preprocess': {
        'denoise': {
            'method': 'bilateral',  # gaussian/median/bilateral
            'gaussian_ksize': (5, 5),
            'gaussian_sigmaX': 1.5,
            'median_ksize': 5,
            'bilateral_d': 9,
            'bilateral_sigmaColor': 75,
            'bilateral_sigmaSpace': 75
        },
        'illumination_correction': {
            'enable': True,
            'clahe_clip_limit': 2.0,
            'clahe_tile_grid_size': (8, 8)
        },
        'geometric_correction': {
            'enable': False,
            'reference_points': [[10,10], [490,10], [490,490], [10,490]],
            'target_size': (500, 500)
        },
        'binary': {
            'method': 'adaptive',  # global/adaptive/otsu
            'global_thresh': 127,
            'adaptive_block_size': 15,
            'adaptive_C': 2,
            'otsu_blur_ksize': (5,5)
        },
        'morphology': {
            'enable': True,
            'kernel_size': (3,3),
            'erosion_iter': 1,
            'dilation_iter': 1,
            'opening_iter': 0,
            'closing_iter': 1
        }
    },
    # 缺陷检测参数
    'detection': {
        'edge_detection': {
            'method': 'canny',  # canny/sobel
            'canny_min_val': 50,
            'canny_max_val': 150,
            'sobel_ksize': 3,
            'sobel_scale': 1,
            'sobel_delta': 0
        },
        'contour': {
            'min_area': 10,  # 最小缺陷面积（像素）
            'max_area': 10000,  # 最大缺陷面积（像素）
            'approx_epsilon': 0.02,  # 轮廓逼近精度
            'hierarchy_level': 0  # 轮廓层级
        },
        'texture': {
            'enable': False,
            'lbp_radius': 1,
            'lbp_points': 8,
            'texture_threshold': 0.2
        }
    },
    # 缺陷分类参数
    'classification': {
        'scratch': {
            'aspect_ratio_min': 5,  # 长宽比阈值
            'solidity_min': 0.8,    # 坚实度阈值
            'area_min': 20
        },
        'dent': {
            'aspect_ratio_max': 2,
            'circularity_min': 0.6,  # 圆度阈值
            'area_min': 50
        },
        'stain': {
            'aspect_ratio_max': 3,
            'solidity_min': 0.5,
            'area_min': 30,
            'color_diff_threshold': 30
        },
        'crack': {
            'aspect_ratio_min': 8,
            'solidity_min': 0.7,
            'area_min': 15,
            'width_max': 5
        }
    },
    # 输出配置
    'output': {
        'save_result_image': True,
        'result_image_dir': 'detection_results',
        'save_report': True,
        'report_dir': 'reports',
        'batch_report_name': 'batch_detection_report.csv',
        'visualization': {
            'draw_contour': True,
            'draw_bounding_box': True,
            'draw_defect_info': True,
            'colors': {
                'scratch': (0, 0, 255),    # 红色
                'dent': (0, 255, 255),     # 黄色
                'stain': (255, 0, 0),      # 蓝色
                'crack': (0, 255, 0),      # 绿色
                'unknown': (128, 128, 128) # 灰色
            }
        }
    },
    # 批处理配置
    'batch_process': {
        'input_dir': 'input_images',
        'recursive': False,
        'supported_formats': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    }
}

# ======================== 日志初始化 ========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('defect_detection.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('IndustrialDefectDetector')

# ======================== 图像预处理模块 ========================
class ImagePreprocessor:
    """图像预处理类：实现降噪、光照校正、几何校正、二值化、形态学操作"""
    
    def __init__(self):
        self.config = CONFIG
        self.logger = logging.getLogger('ImagePreprocessor')
    
    def load_image(self, image_path: str, flag: int = cv2.IMREAD_COLOR) -> Optional[np.ndarray]:
        """加载图像，支持异常处理"""
        try:
            if not os.path.exists(image_path):
                self.logger.error(f"图像文件不存在：{image_path}")
                return None
            
            image = cv2.imread(image_path, flag)
            if image is None:
                self.logger.error(f"读取图像失败：{image_path}（可能格式不支持）")
                return None
            
            self.logger.info(f"成功加载图像：{image_path}，尺寸：{image.shape}")
            return image
        except Exception as e:
            self.logger.error(f"加载图像异常：{e}")
            return None
    
    def denoise(self, image: np.ndarray) -> np.ndarray:
        """图像降噪：支持高斯、中值、双边滤波"""
        try:
            denoise_config = self.config['preprocess']['denoise']
            method = denoise_config['method']
            
            if method == 'gaussian':
                ksize = denoise_config['gaussian_ksize']
                sigmaX = denoise_config['gaussian_sigmaX']
                denoised = cv2.GaussianBlur(image, ksize, sigmaX)
            
            elif method == 'median':
                ksize = denoise_config['median_ksize']
                denoised = cv2.medianBlur(image, ksize)
            
            elif method == 'bilateral':
                d = denoise_config['bilateral_d']
                sigmaColor = denoise_config['bilateral_sigmaColor']
                sigmaSpace = denoise_config['bilateral_sigmaSpace']
                denoised = cv2.bilateralFilter(image, d, sigmaColor, sigmaSpace)
            
            else:
                self.logger.warning(f"未知的降噪方法：{method}，使用原图")
                denoised = image
            
            self.logger.info(f"完成图像降噪，方法：{method}")
            return denoised
        except Exception as e:
            self.logger.error(f"降噪处理失败：{e}，返回原图")
            return image
    
    def illumination_correction(self, image: np.ndarray) -> np.ndarray:
        """光照均衡化：基于CLAHE的自适应直方图均衡化"""
        try:
            config = self.config['preprocess']['illumination_correction']
            if not config['enable']:
                return image
            
            # 转换为灰度图（如果是彩色图）
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # 创建CLAHE对象
            clahe = cv2.createCLAHE(
                clipLimit=config['clahe_clip_limit'],
                tileGridSize=config['clahe_tile_grid_size']
            )
            corrected = clahe.apply(gray)
            
            # 如果原图像是彩色的，转换回彩色
            if len(image.shape) == 3:
                corrected = cv2.cvtColor(corrected, cv2.COLOR_GRAY2BGR)
            
            self.logger.info("完成光照均衡化处理")
            return corrected
        except Exception as e:
            self.logger.error(f"光照校正失败：{e}，返回原图")
            return image
    
    def geometric_correction(self, image: np.ndarray) -> np.ndarray:
        """几何畸变校正：基于透视变换"""
        try:
            config = self.config['preprocess']['geometric_correction']
            if not config['enable']:
                return image
            
            # 获取参考点和目标尺寸
            ref_points = np.array(config['reference_points'], dtype=np.float32)
            target_size = config['target_size']
            target_points = np.array([
                [0, 0],
                [target_size[0]-1, 0],
                [target_size[0]-1, target_size[1]-1],
                [0, target_size[1]-1]
            ], dtype=np.float32)
            
            # 计算透视变换矩阵
            M = cv2.getPerspectiveTransform(ref_points, target_points)
            corrected = cv2.warpPerspective(
                image, M, target_size,
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE
            )
            
            self.logger.info(f"完成几何校正，目标尺寸：{target_size}")
            return corrected
        except Exception as e:
            self.logger.error(f"几何校正失败：{e}，返回原图")
            return image
    
    def to_gray(self, image: np.ndarray) -> np.ndarray:
        """转换为灰度图"""
        try:
            if len(image.shape) == 2:
                return image
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            return gray
        except Exception as e:
            self.logger.error(f"转换灰度图失败：{e}，返回原图")
            return image
    
    def binarization(self, image: np.ndarray) -> np.ndarray:
        """图像二值化：支持全局、自适应、OTSU"""
        try:
            # 转换为灰度图
            gray = self.to_gray(image)
            config = self.config['preprocess']['binary']
            method = config['method']
            
            if method == 'global':
                thresh = config['global_thresh']
                _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY_INV)
            
            elif method == 'adaptive':
                block_size = config['adaptive_block_size']
                # 确保block_size是奇数
                block_size = block_size if block_size % 2 == 1 else block_size + 1
                C = config['adaptive_C']
                binary = cv2.adaptiveThreshold(
                    gray, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY_INV,
                    block_size, C
                )
            
            elif method == 'otsu':
                blur_ksize = config['otsu_blur_ksize']
                blurred = cv2.GaussianBlur(gray, blur_ksize, 0)
                _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            else:
                self.logger.warning(f"未知的二值化方法：{method}，使用OTSU")
                blurred = cv2.GaussianBlur(gray, (5,5), 0)
                _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            self.logger.info(f"完成图像二值化，方法：{method}")
            return binary
        except Exception as e:
            self.logger.error(f"二值化处理失败：{e}，返回灰度图")
            return self.to_gray(image)
    
    def morphology_operation(self, image: np.ndarray) -> np.ndarray:
        """形态学操作：腐蚀、膨胀、开运算、闭运算"""
        try:
            config = self.config['preprocess']['morphology']
            if not config['enable']:
                return image
            
            # 创建结构元素
            kernel_size = config['kernel_size']
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)
            
            # 执行形态学操作
            morph_image = image.copy()
            
            # 腐蚀
            if config['erosion_iter'] > 0:
                morph_image = cv2.erode(
                    morph_image, kernel, 
                    iterations=config['erosion_iter']
                )
            
            # 膨胀
            if config['dilation_iter'] > 0:
                morph_image = cv2.dilate(
                    morph_image, kernel, 
                    iterations=config['dilation_iter']
                )
            
            # 开运算（先腐蚀后膨胀）
            if config['opening_iter'] > 0:
                morph_image = cv2.morphologyEx(
                    morph_image, cv2.MORPH_OPEN, kernel,
                    iterations=config['opening_iter']
                )
            
            # 闭运算（先膨胀后腐蚀）
            if config['closing_iter'] > 0:
                morph_image = cv2.morphologyEx(
                    morph_image, cv2.MORPH_CLOSE, kernel,
                    iterations=config['closing_iter']
                )
            
            self.logger.info("完成形态学操作")
            return morph_image
        except Exception as e:
            self.logger.error(f"形态学操作失败：{e}，返回原图")
            return image
    
    def full_preprocess_pipeline(self, image_path: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
        """完整预处理流水线：加载→几何校正→降噪→光照校正→灰度→二值化→形态学"""
        try:
            # 加载图像
            original = self.load_image(image_path)
            if original is None:
                return None, None, None
            
            # 几何校正
            geo_corrected = self.geometric_correction(original)
            
            # 降噪
            denoised = self.denoise(geo_corrected)
            
            # 光照校正
            illumination_corrected = self.illumination_correction(denoised)
            
            # 转换灰度
            gray = self.to_gray(illumination_corrected)
            
            # 二值化
            binary = self.binarization(illumination_corrected)
            
            # 形态学操作
            morph_binary = self.morphology_operation(binary)
            
            self.logger.info("完整预处理流水线执行完成")
            return original, gray, morph_binary
        except Exception as e:
            self.logger.error(f"预处理流水线执行失败：{e}")
            return None, None, None

# ======================== 缺陷检测与特征提取模块 ========================
class DefectDetector:
    """缺陷检测类：边缘检测、轮廓提取、特征提取、缺陷分类"""
    
    def __init__(self):
        self.config = CONFIG
        self.logger = logging.getLogger('DefectDetector')
    
    def edge_detection(self, gray_image: np.ndarray) -> np.ndarray:
        """边缘检测：Canny/Sobel"""
        try:
            config = self.config['detection']['edge_detection']
            method = config['method']
            
            if method == 'canny':
                min_val = config['canny_min_val']
                max_val = config['canny_max_val']
                edges = cv2.Canny(gray_image, min_val, max_val)
            
            elif method == 'sobel':
                ksize = config['sobel_ksize']
                scale = config['sobel_scale']
                delta = config['sobel_delta']
                
                # Sobel X方向
                sobel_x = cv2.Sobel(
                    gray_image, cv2.CV_64F, 1, 0, 
                    ksize=ksize, scale=scale, delta=delta
                )
                # Sobel Y方向
                sobel_y = cv2.Sobel(
                    gray_image, cv2.CV_64F, 0, 1, 
                    ksize=ksize, scale=scale, delta=delta
                )
                
                # 转换为绝对值并合并
                sobel_x = cv2.convertScaleAbs(sobel_x)
                sobel_y = cv2.convertScaleAbs(sobel_y)
                edges = cv2.addWeighted(sobel_x, 0.5, sobel_y, 0.5, 0)
            
            else:
                self.logger.warning(f"未知的边缘检测方法：{method}，使用Canny")
                edges = cv2.Canny(gray_image, 50, 150)
            
            self.logger.info(f"完成边缘检测，方法：{method}")
            return edges
        except Exception as e:
            self.logger.error(f"边缘检测失败：{e}，返回空图像")
            return np.zeros_like(gray_image)
    
    def extract_contours(self, binary_image: np.ndarray) -> List[np.ndarray]:
        """提取缺陷轮廓：过滤面积异常的轮廓"""
        try:
            config = self.config['detection']['contour']
            min_area = config['min_area']
            max_area = config['max_area']
            
            # 查找轮廓
            contours, hierarchy = cv2.findContours(
                binary_image, 
                cv2.RETR_EXTERNAL, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            # 过滤轮廓（面积筛选）
            filtered_contours = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if min_area <= area <= max_area:
                    filtered_contours.append(cnt)
            
            self.logger.info(f"提取到轮廓总数：{len(contours)}，过滤后：{len(filtered_contours)}")
            return filtered_contours
        except Exception as e:
            self.logger.error(f"提取轮廓失败：{e}，返回空列表")
            return []
    
    def calculate_contour_features(self, contour: np.ndarray) -> Dict:
        """计算轮廓特征：面积、周长、中心、长宽比、圆度、坚实度等"""
        try:
            # 基本特征
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, closed=True) if area > 0 else 0
            
            # 边界矩形
            x, y, w, h = cv2.boundingRect(contour)
            
            # 中心坐标
            M = cv2.moments(contour)
            if M['m00'] > 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
            else:
                cx, cy = x + w//2, y + h//2
            
            # 长宽比
            aspect_ratio = w / h if h > 0 else 0
            
            # 圆度（Circularity）：4πA/P²，完美圆为1
            circularity = (4 * math.pi * area) / (perimeter **2) if perimeter > 0 else 0
            
            # 坚实度（Solidity）：轮廓面积/凸包面积
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 0
            
            # 等效直径
            equivalent_diameter = math.sqrt(4 * area / math.pi) if area > 0 else 0
            
            # 轮廓逼近
            epsilon = self.config['detection']['contour']['approx_epsilon'] * perimeter
            approx_contour = cv2.approxPolyDP(contour, epsilon, closed=True)
            
            features = {
                'area': round(area, 2),
                'perimeter': round(perimeter, 2),
                'bounding_rect': (x, y, w, h),
                'center': (cx, cy),
                'aspect_ratio': round(aspect_ratio, 2),
                'circularity': round(circularity, 2),
                'solidity': round(solidity, 2),
                'equivalent_diameter': round(equivalent_diameter, 2),
                'approx_contour': approx_contour,
                'width': w,
                'height': h
            }
            
            return features
        except Exception as e:
            self.logger.error(f"计算轮廓特征失败：{e}")
            return {}
    
    def classify_defect(self, features: Dict) -> str:
        """缺陷分类：划痕/凹坑/污渍/裂纹/未知"""
        try:
            if not features:
                return 'unknown'
            
            config = self.config['classification']
            
            # 划痕特征：长宽比大，坚实度高
            if (features['aspect_ratio'] >= config['scratch']['aspect_ratio_min'] and
                features['solidity'] >= config['scratch']['solidity_min'] and
                features['area'] >= config['scratch']['area_min']):
                return 'scratch'
            
            # 裂纹特征：长宽比极大，宽度小
            elif (features['aspect_ratio'] >= config['crack']['aspect_ratio_min'] and
                  features['width'] <= config['crack']['width_max'] and
                  features['area'] >= config['crack']['area_min'] and
                  features['solidity'] >= config['crack']['solidity_min']):
                return 'crack'
            
            # 凹坑特征：圆度高，长宽比小
            elif (features['circularity'] >= config['dent']['circularity_min'] and
                  features['aspect_ratio'] <= config['dent']['aspect_ratio_max'] and
                  features['area'] >= config['dent']['area_min']):
                return 'dent'
            
            # 污渍特征：长宽比适中，坚实度中等
            elif (features['aspect_ratio'] <= config['stain']['aspect_ratio_max'] and
                  features['solidity'] >= config['stain']['solidity_min'] and
                  features['area'] >= config['stain']['area_min']):
                return 'stain'
            
            else:
                return 'unknown'
        except Exception as e:
            self.logger.error(f"缺陷分类失败：{e}")
            return 'unknown'
    
    def detect_defects(self, gray_image: np.ndarray, binary_image: np.ndarray) -> List[Dict]:
        """完整缺陷检测流程：边缘检测→轮廓提取→特征计算→分类"""
        try:
            # 边缘检测（辅助轮廓提取）
            edges = self.edge_detection(gray_image)
            
            # 提取轮廓
            contours = self.extract_contours(binary_image)
            
            # 对每个轮廓计算特征并分类
            defect_list = []
            for idx, contour in enumerate(contours):
                # 计算特征
                features = self.calculate_contour_features(contour)
                if not features:
                    continue
                
                # 分类
                defect_type = self.classify_defect(features)
                
                # 构建缺陷信息
                defect_info = {
                    'defect_id': idx + 1,
                    'defect_type': defect_type,
                    'features': features,
                    'contour': contour
                }
                defect_list.append(defect_info)
            
            self.logger.info(f"检测到缺陷数量：{len(defect_list)}")
            return defect_list
        except Exception as e:
            self.logger.error(f"缺陷检测流程失败：{e}")
            return []

# ======================== 结果可视化与报告生成模块 ========================
class ResultVisualizer:
    """结果可视化与报告生成类"""
    
    def __init__(self):
        self.config = CONFIG
        self.logger = logging.getLogger('ResultVisualizer')
        
        # 创建输出目录
        self.result_image_dir = self.config['output']['result_image_dir']
        self.report_dir = self.config['output']['report_dir']
        
        if not os.path.exists(self.result_image_dir):
            os.makedirs(self.result_image_dir)
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)
    
    def draw_defects(self, original_image: np.ndarray, defect_list: List[Dict]) -> np.ndarray:
        """在原图上绘制缺陷标注：轮廓、边界框、缺陷信息"""
        try:
            vis_image = original_image.copy()
            config = self.config['output']['visualization']
            colors = config['colors']
            
            for defect in defect_list:
                defect_id = defect['defect_id']
                defect_type = defect['defect_type']
                features = defect['features']
                contour = defect['contour']
                
                # 获取颜色
                color = colors.get(defect_type, colors['unknown'])
                
                # 绘制轮廓
                if config['draw_contour']:
                    cv2.drawContours(vis_image, [contour], -1, color, 2)
                
                # 绘制边界框
                if config['draw_bounding_box']:
                    x, y, w, h = features['bounding_rect']
                    cv2.rectangle(vis_image, (x, y), (x+w, y+h), color, 2)
                
                # 绘制缺陷信息
                if config['draw_defect_info']:
                    cx, cy = features['center']
                    info_text = f"ID:{defect_id} | {defect_type} | Area:{features['area']}"
                    cv2.putText(
                        vis_image, info_text, (cx-50, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1
                    )
            
            # 添加总标题
            total_defects = len(defect_list)
            status_text = f"Defect Detection Result | Total Defects: {total_defects}"
            cv2.putText(
                vis_image, status_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2
            )
            
            self.logger.info("完成缺陷标注绘制")
            return vis_image
        except Exception as e:
            self.logger.error(f"绘制缺陷标注失败：{e}，返回原图")
            return original_image
    
    def save_result_image(self, image: np.ndarray, image_name: str) -> str:
        """保存检测结果图像"""
        try:
            # 生成保存路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_name = f"{os.path.splitext(image_name)[0]}_{timestamp}.jpg"
            save_path = os.path.join(self.result_image_dir, save_name)
            
            # 保存图像
            cv2.imwrite(save_path, image)
            self.logger.info(f"结果图像已保存：{save_path}")
            return save_path
        except Exception as e:
            self.logger.error(f"保存结果图像失败：{e}")
            return ""
    
    def generate_defect_report(self, image_path: str, defect_list: List[Dict], save_image_path: str = "") -> Dict:
        """生成单张图像的缺陷检测报告"""
        try:
            # 基础信息
            report = {
                'image_path': image_path,
                'image_name': os.path.basename(image_path),
                'detection_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_defects': len(defect_list),
                'defect_details': [],
                'result_image_path': save_image_path,
                'detection_status': 'SUCCESS' if len(defect_list) >= 0 else 'FAILED'
            }
            
            # 缺陷详情
            for defect in defect_list:
                defect_detail = {
                    'defect_id': defect['defect_id'],
                    'defect_type': defect['defect_type'],
                    'area': defect['features']['area'],
                    'perimeter': defect['features']['perimeter'],
                    'center_coordinate': defect['features']['center'],
                    'bounding_rect': defect['features']['bounding_rect'],
                    'aspect_ratio': defect['features']['aspect_ratio'],
                    'circularity': defect['features']['circularity'],
                    'solidity': defect['features']['solidity']
                }
                report['defect_details'].append(defect_detail)
            
            self.logger.info(f"生成单张图像检测报告：{image_path}")
            return report
        except Exception as e:
            self.logger.error(f"生成缺陷报告失败：{e}")
            return {
                'image_path': image_path,
                'detection_status': 'FAILED',
                'error_message': str(e)
            }
    
    def save_batch_report(self, batch_reports: List[Dict]) -> str:
        """保存批量检测报告（CSV格式）"""
        try:
            # 生成报告路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"batch_report_{timestamp}.csv"
            if self.config['output']['batch_report_name']:
                report_name = self.config['output']['batch_report_name'].replace('.csv', f'_{timestamp}.csv')
            report_path = os.path.join(self.report_dir, report_name)
            
            # 写入CSV
            with open(report_path, 'w', newline='', encoding='utf-8') as f:
                # 主表头
                fieldnames = [
                    'image_name', 'detection_time', 'total_defects',
                    'scratch_count', 'dent_count', 'stain_count',
                    'crack_count', 'unknown_count', 'detection_status',
                    'result_image_path'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                # 写入每行数据
                for report in batch_reports:
                    # 统计各类型缺陷数量
                    scratch_count = 0
                    dent_count = 0
                    stain_count = 0
                    crack_count = 0
                    unknown_count = 0
                    
                    for defect in report.get('defect_details', []):
                        if defect['defect_type'] == 'scratch':
                            scratch_count += 1
                        elif defect['defect_type'] == 'dent':
                            dent_count += 1
                        elif defect['defect_type'] == 'stain':
                            stain_count += 1
                        elif defect['defect_type'] == 'crack':
                            crack_count += 1
                        else:
                            unknown_count += 1
                    
                    # 构建行数据
                    row_data = {
                        'image_name': report.get('image_name', ''),
                        'detection_time': report.get('detection_time', ''),
                        'total_defects': report.get('total_defects', 0),
                        'scratch_count': scratch_count,
                        'dent_count': dent_count,
                        'stain_count': stain_count,
                        'crack_count': crack_count,
                        'unknown_count': unknown_count,
                        'detection_status': report.get('detection_status', 'FAILED'),
                        'result_image_path': report.get('result_image_path', '')
                    }
                    writer.writerow(row_data)
            
            self.logger.info(f"批量检测报告已保存：{report_path}")
            return report_path
        except Exception as e:
            self.logger.error(f"保存批量报告失败：{e}")
            return ""

# ======================== 批量处理模块 ========================
class BatchProcessor:
    """批量图像处理类"""
    
    def __init__(self):
        self.config = CONFIG
        self.logger = logging.getLogger('BatchProcessor')
        
        # 初始化子模块
        self.preprocessor = ImagePreprocessor()
        self.detector = DefectDetector()
        self.visualizer = ResultVisualizer()
    
    def get_image_list(self, input_dir: Optional[str] = None) -> List[str]:
        """获取待处理图像列表"""
        try:
            input_dir = input_dir or self.config['batch_process']['input_dir']
            if not os.path.exists(input_dir):
                self.logger.error(f"输入目录不存在：{input_dir}")
                return []
            
            supported_formats = self.config['batch_process']['supported_formats']
            image_list = []
            
            # 遍历目录
            for root, dirs, files in os.walk(input_dir):
                for file in files:
                    # 检查文件格式
                    if os.path.splitext(file)[1].lower() in supported_formats:
                        image_path = os.path.join(root, file)
                        image_list.append(image_path)
                
                # 是否递归子目录
                if not self.config['batch_process']['recursive']:
                    break
            
            self.logger.info(f"找到待处理图像数量：{len(image_list)}")
            return image_list
        except Exception as e:
            self.logger.error(f"获取图像列表失败：{e}")
            return []
    
    def process_single_image(self, image_path: str, show_result: bool = False) -> Dict:
        """处理单张图像"""
        try:
            self.logger.info(f"开始处理图像：{image_path}")
            
            # 1. 预处理
            original, gray, binary = self.preprocessor.full_preprocess_pipeline(image_path)
            if original is None:
                return self.visualizer.generate_defect_report(
                    image_path, [], ""
                )
            
            # 2. 缺陷检测
            defect_list = self.detector.detect_defects(gray, binary)
            
            # 3. 结果可视化
            vis_image = self.visualizer.draw_defects(original, defect_list)
            
            # 4. 保存结果图像
            save_image_path = ""
            if self.config['output']['save_result_image']:
                save_image_path = self.visualizer.save_result_image(
                    vis_image, os.path.basename(image_path)
                )
            
            # 5. 显示结果（可选）
            if show_result:
                cv2.namedWindow('Defect Detection Result', cv2.WINDOW_NORMAL)
                cv2.imshow('Defect Detection Result', vis_image)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            
            # 6. 生成报告
            report = self.visualizer.generate_defect_report(
                image_path, defect_list, save_image_path
            )
            
            self.logger.info(f"完成图像处理：{image_path}")
            return report
        except Exception as e:
            self.logger.error(f"处理单张图像失败：{e}")
            return self.visualizer.generate_defect_report(
                image_path, [], ""
            )
    
    def process_batch_images(self, input_dir: Optional[str] = None, show_result: bool = False) -> Tuple[List[Dict], str]:
        """批量处理图像"""
        try:
            self.logger.info("开始批量图像处理")
            
            # 获取图像列表
            image_list = self.get_image_list(input_dir)
            if not image_list:
                self.logger.warning("没有待处理图像")
                return [], ""
            
            # 处理每张图像
            batch_reports = []
            total_images = len(image_list)
            success_count = 0
            
            for idx, image_path in enumerate(image_list):
                self.logger.info(f"处理进度：{idx+1}/{total_images}")
                report = self.process_single_image(image_path, show_result)
                batch_reports.append(report)
                
                if report.get('detection_status') == 'SUCCESS':
                    success_count += 1
            
            # 生成批量报告
            batch_report_path = ""
            if self.config['output']['save_report']:
                batch_report_path = self.visualizer.save_batch_report(batch_reports)
            
            # 打印统计信息
            self.logger.info(f"""
批量处理完成：
- 总图像数：{total_images}
- 成功处理：{success_count}
- 失败数量：{total_images - success_count}
- 批量报告路径：{batch_report_path}
            """)
            
            return batch_reports, batch_report_path
        except Exception as e:
            self.logger.error(f"批量处理失败：{e}")
            return [], ""

# ======================== 主程序入口 ========================
def main():
    """主函数：提供交互式界面，支持单张/批量处理"""
    try:
        # 初始化批量处理器
        batch_processor = BatchProcessor()
        logger.info("工业级缺陷检测系统初始化完成")
        
        # 交互式菜单
        while True:
            print("\n===== 工业级产品表面缺陷检测系统 =====")
            print("1. 处理单张图像")
            print("2. 批量处理图像")
            print("3. 自动模式（处理默认目录）")
            print("4. 退出系统")
            print("======================================")
            
            choice = input("请输入操作选项（1-4）：")
            
            if choice == '1':
                # 处理单张图像
                image_path = input("请输入图像文件路径：").strip()
                if not os.path.exists(image_path):
                    print("图像文件不存在！")
                    continue
                
                batch_processor.process_single_image(image_path, show_result=True)
            
            elif choice == '2':
                # 批量处理图像
                input_dir = input(f"请输入图像目录（默认：{CONFIG['batch_process']['input_dir']}）：").strip()
                input_dir = input_dir or CONFIG['batch_process']['input_dir']
                batch_processor.process_batch_images(input_dir, show_result=False)
            
            elif choice == '3':
                # 自动模式：处理默认目录
                print("进入自动模式...")
                print(f"正在处理默认目录：{CONFIG['batch_process']['input_dir']}")
                
                # 检查默认目录是否存在，不存在则创建
                input_dir = CONFIG['batch_process']['input_dir']
                if not os.path.exists(input_dir):
                    print(f"默认目录不存在，正在创建：{input_dir}")
                    os.makedirs(input_dir)
                    print("目录创建成功，请将图像放入该目录后重新运行")
                    continue
                
                batch_processor.process_batch_images(input_dir, show_result=False)
                print("自动模式处理完成！")
            
            elif choice == '4':
                # 退出系统
                print("感谢使用工业级缺陷检测系统，再见！")
                break
            
            else:
                print("无效的选项，请重新输入！")
    
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        print("\n程序已被用户中断")
    except Exception as e:
        logger.error(f"主程序执行失败：{e}")
        print(f"程序执行出错：{e}")

# ======================== 程序入口 ========================
if __name__ == "__main__":
    # 设置OpenCV中文显示支持（可选）
    cv2.putText = lambda img, text, org, fontFace, fontScale, color, thickness, lineType=None, bottomLeftOrigin=None: \
        cv2.putText(img, text, org, fontFace, fontScale, color, thickness, cv2.LINE_AA if lineType is None else lineType, bottomLeftOrigin)
    
    # 启动主程序
    main()