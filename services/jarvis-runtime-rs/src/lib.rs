use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ExecutionEnvelope { pub execution_id: String, pub action_type: String, pub target: String }

pub fn canonical_digest(envelope: &ExecutionEnvelope) -> String {
    let bytes = serde_json::to_vec(envelope).expect("serializable envelope");
    let mut h = Sha256::new(); h.update(bytes); format!("{:x}", h.finalize())
}

pub fn deny_by_default(authorized: bool) -> Result<(), &'static str> {
    if authorized { Ok(()) } else { Err("execution_not_authorized") }
}
