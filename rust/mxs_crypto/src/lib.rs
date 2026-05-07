use rand::{distributions::Alphanumeric, Rng};
use sha2::{Digest, Sha256};

pub fn hash_string(input: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    hex::encode(hasher.finalize())
}

pub fn random_token(len: usize) -> String {
    rand::thread_rng()
        .sample_iter(&Alphanumeric)
        .take(len)
        .map(char::from)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn token_len() {
        assert_eq!(random_token(32).len(), 32);
    }
}
