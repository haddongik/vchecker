USE battle_versions;

CREATE TABLE versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    target VARCHAR(50) NOT NULL COMMENT '대상 플랫폼',
    build_tag VARCHAR(100) NOT NULL COMMENT '빌드 태그',
    repo_root TEXT COMMENT '레포지토리 루트',
    script_hash VARCHAR(255) COMMENT '스크립트 해시',
    db_hash VARCHAR(255) COMMENT '데이터베이스 해시',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_target (target),
    INDEX idx_build_tag (build_tag),
    INDEX idx_created_at (created_at),
    UNIQUE KEY unique_target_build (target, build_tag)
); 