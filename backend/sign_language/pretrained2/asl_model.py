import torch
import torch.nn as nn


class ImprovedASLModel(nn.Module):

    def __init__(self, num_classes=77):
        super().__init__()

        # ============================================================
        # INPUT:
        # [batch, sequence, 2 hands, 21 landmarks, 3 coordinates]
        #
        # 2 × 21 × 3 = 126 features
        # ============================================================

        self.conv_layers = nn.Sequential(

            # 126 -> 128
            nn.Conv1d(
                in_channels=126,
                out_channels=128,
                kernel_size=3,
                padding=1
            ),

            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),

            # 128 -> 256
            nn.Conv1d(
                in_channels=128,
                out_channels=256,
                kernel_size=3,
                padding=1
            ),

            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
        )

        # ============================================================
        # BIDIRECTIONAL LSTM
        # ============================================================

        self.lstm = nn.LSTM(
            input_size=256,
            hidden_size=256,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=0.3
        )

        # ============================================================
        # ATTENTION
        #
        # LSTM output = 512
        # ============================================================

        self.attention = nn.Sequential(
            nn.Linear(512, 128),
            nn.Tanh(),
            nn.Linear(128, 1)
        )

        # ============================================================
        # CLASSIFIER
        # ============================================================

        self.classifier = nn.Sequential(

            nn.Linear(512, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(256, num_classes)
        )

    def forward(self, x, mask=None):

        # ------------------------------------------------------------
        # Expected input:
        #
        # [batch, sequence, 2, 21, 3]
        # ------------------------------------------------------------

        batch_size, seq_len, hands, landmarks, coords = x.shape

        # ------------------------------------------------------------
        # Flatten:
        #
        # 2 × 21 × 3 = 126
        #
        # [B, S, 2, 21, 3]
        # ->
        # [B, S, 126]
        # ------------------------------------------------------------

        x = x.reshape(
            batch_size,
            seq_len,
            126
        )

        # ------------------------------------------------------------
        # Conv1D expects:
        #
        # [B, channels, sequence]
        #
        # [B, S, 126]
        # ->
        # [B, 126, S]
        # ------------------------------------------------------------

        x = x.transpose(1, 2)

        # ------------------------------------------------------------
        # CNN
        # ------------------------------------------------------------

        x = self.conv_layers(x)

        # ------------------------------------------------------------
        # Back to:
        #
        # [B, S, 256]
        # ------------------------------------------------------------

        x = x.transpose(1, 2)

        # ------------------------------------------------------------
        # LSTM
        #
        # Output:
        # [B, S, 512]
        # ------------------------------------------------------------

        x, _ = self.lstm(x)

        # ------------------------------------------------------------
        # Attention
        #
        # scores:
        # [B, S, 1]
        # ------------------------------------------------------------

        scores = self.attention(x)

        weights = torch.softmax(
            scores,
            dim=1
        )

        # Weighted sum over sequence
        #
        # [B, S, 512]
        # ->
        # [B, 512]
        # ------------------------------------------------------------

        x = torch.sum(
            weights * x,
            dim=1
        )

        # ------------------------------------------------------------
        # Classifier
        #
        # [B, 512]
        # ->
        # [B, 77]
        # ------------------------------------------------------------

        x = self.classifier(x)

        return x