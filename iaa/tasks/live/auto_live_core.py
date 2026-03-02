import time
import logging

import cv2
import numpy as np

from kotonebot.client.host.mumu12_host import MuMu12HostConfig, Mumu12V5Host
from kotonebot.backend.image import find
from kotonebot.primitives import Rect
from kotonebot.client import Device

logger = logging.getLogger(__name__)

class RhythmGameAnalyzer:
    BASE_WIDTH = 1280
    BASE_HEIGHT = 720

    def __init__(self, device: Device, life_img, num_lanes=6, debug_frame=None, stop_check=None, debug=False):
        self.device = device
        self.debug_frame = debug_frame
        self.stop_check = stop_check
        self.debug = debug
        
        # 加载 LIFE 图像用于检测是否在 live 界面
        self.LIFE = life_img
        assert self.LIFE is not None, 'Failed to load life.png'
        
        # === 核心配置参数 ===
        self.num_lanes = num_lanes
        self.judgement_line_y_ratio = 0.74
        self.margin_side_ratio = 0.10 
        self.box_height = 40
        self.lookahead_gap_px = 0      # 判定线上方 look 区域的像素偏移
        self.lookahead_box_height = 25   # look 区域高度，可独立调节
        self.lane_inner_padding = 10
        
        # === 阈值设置 ===
        # 1. 触发阈值 (严格，用于按下)
        self.trigger_brightness = 220
        
        # 2. 保持阈值 (宽松，用于 Hold 过程中不松手)
        # Hold 长条中间通常比较均匀，Std 会很低，所以保持时不要校验 Std
        self.sustain_brightness = 150  # 稍微低一点，防止长条变暗断触
        self.lookahead_brightness = self.sustain_brightness
        
        # === 状态管理 ===
        self.paused = False
        
        # 轨道状态: False=空闲, True=按下
        self.lane_states = [False] * num_lanes
        
        # 容错计数器: 记录连续没检测到 Note 的帧数
        # 用于防止长条中间偶尔一帧识别失败导致的断触，以及延迟尾判松手时机
        self.lane_empty_counters = [0] * num_lanes

    def calculate_sharpness(self, gray_roi):
        if gray_roi.size == 0: return 0
        laplacian = cv2.Laplacian(gray_roi, cv2.CV_64F)
        return laplacian.var()

    def get_lane_regions(self, frame_width, frame_height):
        regions = []
        total_valid_width = frame_width * (1 - 2 * self.margin_side_ratio)
        lane_width = total_valid_width / self.num_lanes
        start_x = frame_width * self.margin_side_ratio
        base_y = int(frame_height * self.judgement_line_y_ratio)
        lane_inner_padding = self.lane_inner_padding
        lane_width_reduction = lane_inner_padding * 2
        box_height = self.box_height
        lookahead_gap_px = self.lookahead_gap_px
        lookahead_box_height = self.lookahead_box_height
        
        for i in range(self.num_lanes):
            lane_x = int(start_x + i * lane_width)
            # 主判定区
            main_rect = (lane_x + lane_inner_padding, base_y, int(lane_width) - lane_width_reduction, box_height)
            # 前视区 (用于判断是否是 Hold)
            # gap 以主判定框的上边为基准：主框顶到 look 框底部的垂直距离为 lookahead_gap_px
            look_y = max(0, base_y - lookahead_gap_px - lookahead_box_height)
            look_rect = (lane_x + lane_inner_padding, look_y, int(lane_width) - lane_width_reduction, lookahead_box_height)
            regions.append((main_rect, look_rect))
        return regions, int(base_y)

    def logic_to_physical_touch_point(self, x: int, y: int) -> tuple[int, int]:
        if not self.device:
            return x, y
        px, py = self.device.scaler.logic_to_physical((x, y))
        return int(px), int(py)

    def analyze_region(self, gray_img, rect):
        x, y, w, h = rect
        roi = gray_img[y:y+h, x:x+w]
        if roi.size == 0: return 0, 0, 0
        mean, std = cv2.meanStdDev(roi)
        sharpness = self.calculate_sharpness(roi)
        return mean[0][0], std[0][0], sharpness

    def process_screenshot(self):
        # 1. 获取图像
        if self.debug_frame is not None:
            original_frame = self.debug_frame.copy()
        else:
            original_frame = self.device.screenshot()
            if original_frame is None: return None

        frame = cv2.resize(original_frame, (self.BASE_WIDTH, self.BASE_HEIGHT))

        # 检查是否在 live 界面
        if not find(frame, self.LIFE, rect=Rect(1010, 14, 50, 30)):
            cv2.putText(frame, 'NOT AT LIVE', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)
            return frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = frame.shape[:2]
        regions, judge_y = self.get_lane_regions(w, h)
        cv2.line(frame, (0, judge_y), (w, judge_y), (255, 100, 100), 2)

        # 2. 遍历轨道处理
        for i, (main_rect, look_rect) in enumerate(regions):
            mx, my, mw, mh = main_rect
            
            # --- 图像分析 ---
            m_mean, m_std, m_sharpness = self.analyze_region(gray, main_rect)
            l_mean, l_std, l_sharpness = self.analyze_region(gray, look_rect)
            
            # --- 核心逻辑：双重标准 + look ahead ---
            main_active = False
            look_active = False
            is_active = False

            if self.lane_states[i]:
                # 【保持模式】：宽松标准，使用 look ahead 预判尾判
                main_active = m_mean > self.sustain_brightness
                look_active = l_mean > self.lookahead_brightness
                is_active = main_active or look_active
            else:
                # 【触发模式】：严格标准，只看主判定区
                if m_mean > self.trigger_brightness:
                    is_active = True
                    main_active = True

            # --- 状态机控制 (含防抖) ---
            center_x = mx + mw // 2
            center_y = my + mh // 2
            touch_id = i  # 使用轨道索引作为手指ID，互不干扰

            if not self.lane_states[i]:
                if is_active:
                    # 状态：空 -> 有
                    if self.device:
                        tx, ty = self.logic_to_physical_touch_point(center_x, center_y)
                        self.device.multi_touch.multi_touch_down(tx, ty, touch_id)
                        print('down', i, tx, ty, f'(base:{center_x},{center_y})')
                    self.lane_states[i] = True
                    self.lane_empty_counters[i] = 0
                    # self.lookahead_empty_counters[i] = 0
            else:
                # 已按下，维护/释放逻辑
                if main_active or look_active:
                    self.lane_empty_counters[i] = 0
                else:
                    self.lane_empty_counters[i] += 1

                if not look_active:
                    if self.device:
                        tx, ty = self.logic_to_physical_touch_point(center_x, center_y)
                        self.device.multi_touch.multi_touch_up(tx, ty, touch_id)
                        print('  up', i, tx, ty, f'(base:{center_x},{center_y})')
                    self.lane_states[i] = False
                    self.lane_empty_counters[i] = 0
            
            # --- 可视化调试文本 (回归) ---
            # 根据状态决定框颜色
            if self.lane_states[i]:
                if is_active:
                    color = (0, 255, 0) # 绿色：正在按压且检测到信号
                    state_text = "HOLD"
            else:
                if m_mean > self.trigger_brightness:
                    color = (255, 0, 255) # 紫色：亮度够但被 Sharpness 过滤 (疑似闪光)
                else:
                    color = (0, 0, 255) # 红色：无信号
                state_text = ""

            cv2.rectangle(frame, (mx, my), (mx+mw, my+mh), color, 2)
            # look ahead 区域可视化
            lx, ly, lw, lh = look_rect
            look_color = (0, 150, 255) if look_active else (100, 100, 100)
            cv2.rectangle(frame, (lx, ly), (lx+lw, ly+lh), look_color, 1)
            
            # 调试数据显式
            y_off = my + mh + 20
            # 简写 M/S/Sh 节省空间
            info = f"M:{int(m_mean)} S:{int(m_std)} Sh:{int(m_sharpness)}"
            cv2.putText(frame, info, (mx, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            # look ahead 数据
            look_info = f"L:{int(l_mean)} Sh:{int(l_sharpness)}"
            cv2.putText(frame, look_info, (lx, ly - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
            if state_text:
                cv2.putText(frame, state_text, (mx, my + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        return frame

    def run(self):
        if self.debug:
            print("开始运行... 按 'q' 退出，按 '空格' 暂停")
        while True:
            t0 = time.time()
            frame = self.process_screenshot()
            if frame is None: continue
            
            if self.stop_check and self.stop_check():
                logger.info("Stop check triggered, exiting analyzer loop.")
                break
            
            if self.debug:
                fps = 1 / (time.time() - t0 + 1e-6)
                cv2.putText(frame, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                cv2.imshow('PJSK Auto', cv2.resize(frame, None, fx=0.6, fy=0.6))
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord(' '):
                    self.paused = not self.paused
                    print(f"暂停状态: {self.paused}")
                    if self.paused:
                        # 暂停时强制松开所有手指，防止鬼畜
                        if self.device:
                            for i in range(self.num_lanes):
                                self.device.multi_touch.multi_touch_up(0, 0, i)
                        cv2.waitKey(0)
            
        if self.device:
            for i in range(self.num_lanes):
                self.device.multi_touch.multi_touch_up(0, 0, i)
        
        if self.debug:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    # === 调试配置 ===
    USE_DEBUG_IMAGE = False  # 设为 True 时使用本地单张图片调试
    DEBUG_IMAGE_PATH = r"./glow.png"  # 指向要调试的图片路径

    debug_frame = None
    if USE_DEBUG_IMAGE:
        debug_frame = cv2.imread(DEBUG_IMAGE_PATH)

    d = None
    if not USE_DEBUG_IMAGE:
        mumu = Mumu12V5Host.list()[0]
        d = mumu.create_device('nemu_ipc', MuMu12HostConfig())

    LIFE = cv2.imread('life.png')
    assert LIFE is not None, 'Failed to load life.png'
    assert d is not None
    analyzer = RhythmGameAnalyzer(d, LIFE, num_lanes=6, debug_frame=debug_frame, debug=True)
    analyzer.run()
